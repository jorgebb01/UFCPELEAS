"""Informe ejecutivo en PDF: convierte final/informe_ejecutivo.md con markdown + xhtml2pdf (D-35).

El PDF es solo un cambio de formato: no añade cifras. `verificar_pdf` extrae el texto del PDF con pypdf y
comprueba que contiene todas las apariciones de IDs de cifra (C-xxx) y números del .md y ningún ID ni número
que no esté en el .md. Las repeticiones se toleran solo en sentido PDF > .md, porque xhtml2pdf repite la cabecera
de una tabla cuando la tabla continúa en la página siguiente.
"""

from __future__ import annotations

import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

import markdown
import reportlab
from pypdf import PdfReader
from reportlab import rl_config
from xhtml2pdf import pisa

from ufcpeleas.models import rutas
from ufcpeleas.models.informe import INFORME

INFORME_PDF: Path = rutas.FINAL / "informe_ejecutivo.pdf"

#: Fuente Bitstream Vera, incluida en el paquete reportlab (versión fijada en uv.lock): cubre acentos, ñ, ¿, –, −, ≈ y ·.
_FUENTES: Path = Path(reportlab.__file__).resolve().parent / "fonts"

#: Encabezado que separa el cuerpo del informe (máximo 3 páginas) del anexo de cifras.
_ANEXO = "## Anexo: cifras citadas"

#: Pie de página: único texto del PDF que no procede del .md (se descarta al comparar).
_PIE = "Caso CD-726-017 · Informe ejecutivo · página"
_RE_PIE = re.compile(re.escape(_PIE) + r"\s*\d+\s*de\s*\d+")

#: Anchos de las columnas del anexo (ID, Valor, Descripción, Archivo, Localizador, Transformación).
_ANCHOS_ANEXO: tuple[str, ...] = ("5%", "7%", "33%", "20%", "26%", "9%")

_RE_ID = re.compile(r"C-\d{3}")
#: Números tal como se escriben en el informe (coma o punto decimal, signo opcional), fuera de los IDs C-xxx.
_RE_NUM = re.compile(r"(?<![\w-])-?\d+(?:[.,]\d+)?")

_CSS = """
@font-face {{ font-family: Vera; src: url("{d}/Vera.ttf"); }}
@font-face {{ font-family: Vera; src: url("{d}/VeraBd.ttf"); font-weight: bold; }}
@font-face {{ font-family: Vera; src: url("{d}/VeraIt.ttf"); font-style: italic; }}
@font-face {{ font-family: Vera; src: url("{d}/VeraBI.ttf"); font-weight: bold; font-style: italic; }}
@page {{
  size: a4;
  margin: 1.6cm 1.7cm 1.8cm 1.7cm;
  @frame pie {{ -pdf-frame-content: pie; bottom: 0.8cm; margin-left: 1.7cm; margin-right: 1.7cm; height: 0.6cm; }}
}}
@page anexo {{
  size: a4 landscape;
  margin: 1.4cm 1.6cm 1.6cm 1.6cm;
  @frame pie {{ -pdf-frame-content: pie; bottom: 0.6cm; margin-left: 1.6cm; margin-right: 1.6cm; height: 0.6cm; }}
}}
body {{ font-family: Vera; font-size: 9.2pt; line-height: 1.25; color: #111111; }}
h1 {{ font-size: 15pt; margin: 0 0 4pt 0; }}
h2 {{ font-size: 11.5pt; margin: 7pt 0 2pt 0; color: #1f3a5f; }}
p {{ margin: 0 0 4pt 0; }}
ul, ol {{ margin: 0 0 4pt 0; }}
li {{ margin: 0 0 2pt 0; }}
code {{ font-family: Vera; background-color: #eeeeee; }}
table {{ border: 0.5pt solid #888888; margin: 2pt 0 5pt 0; }}
th {{ background-color: #dde4ee; font-weight: bold; padding: 2pt; border: 0.5pt solid #888888; }}
td {{ padding: 2pt; border: 0.5pt solid #888888; vertical-align: top; }}
.anexo {{ font-size: 6.8pt; line-height: 1.2; }}
.anexo h2 {{ font-size: 10.5pt; }}
.anexo td, .anexo th {{ padding: 1.2pt; }}
#pie {{ font-size: 7pt; color: #666666; text-align: center; }}
"""


class ErrorInformePdf(Exception):
    """El PDF no reproduce las cifras del informe .md."""


@dataclass
class ComparacionPdf:
    """Resultado de comparar el texto del PDF con el .md de origen."""

    paginas: int
    paginas_cuerpo: int
    ids_md: int
    numeros_md: int
    ids_faltan: list[str] = field(default_factory=list)
    ids_sobran: list[str] = field(default_factory=list)
    numeros_faltan: list[str] = field(default_factory=list)
    numeros_sobran: list[str] = field(default_factory=list)

    @property
    def correcta(self) -> bool:
        """True si no falta ninguna aparición del .md y no aparece en el PDF ningún ID o número ajeno al .md."""
        return not (self.ids_faltan or self.ids_sobran or self.numeros_faltan or self.numeros_sobran)


def _html(texto_md: str, sha256_md: str) -> str:
    """HTML del informe: cuerpo en A4 vertical y anexo en A4 apaisado (letra menor); el hash del .md va en los metadatos."""
    cuerpo, _, anexo = texto_md.partition(_ANEXO)
    html_cuerpo = markdown.markdown(cuerpo, extensions=["tables"])
    html_anexo = markdown.markdown(_ANEXO + anexo, extensions=["tables"]) if anexo else ""
    anchos = iter(_ANCHOS_ANEXO)
    html_anexo = re.sub(r"<th>", lambda _: f"<th width='{next(anchos, '')}'>", html_anexo)
    titulo = escape(cuerpo.splitlines()[0].lstrip("# ").strip()) if cuerpo else "Informe ejecutivo"
    return (
        "<html><head><meta charset='utf-8'>"
        f"<title>{titulo}</title>"
        f"<meta name='author' content='{escape(rutas.RESPONSABLE)}'>"
        f"<meta name='subject' content='Generado desde {rutas.relativa(INFORME)} (SHA-256 {sha256_md})'>"
        f"<style>{_CSS.format(d=_FUENTES.as_posix())}</style></head><body>"
        f"<div id='pie'>{escape(_PIE)} <pdf:pagenumber> de <pdf:pagecount></div>"
        f"{html_cuerpo}"
        + (f"<pdf:nexttemplate name='anexo' /><pdf:nextpage /><div class='anexo'>{html_anexo}</div>" if html_anexo else "")
        + "</body></html>"
    )


def generar_pdf(ruta_md: Path = INFORME, ruta_salida: Path = INFORME_PDF) -> Path:
    """Genera final/informe_ejecutivo.pdf desde el .md (salida determinista) y verifica que conserva todas las cifras."""
    datos_md = ruta_md.read_bytes()
    texto_md = datos_md.decode("utf-8")
    html = _html(texto_md, hashlib.sha256(datos_md).hexdigest())
    salida = rutas.comprobar_escritura(ruta_salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    invariante_previo = rl_config.invariant
    rl_config.invariant = 1  # sin fecha de creación ni ID aleatorio: el mismo .md da el mismo PDF byte a byte
    try:
        buffer = io.BytesIO()
        resultado = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    finally:
        rl_config.invariant = invariante_previo
    if resultado.err:
        raise ErrorInformePdf(f"xhtml2pdf devolvió {resultado.err} errores al convertir {rutas.relativa(ruta_md)}")
    salida.write_bytes(buffer.getvalue())
    comp = verificar_pdf(ruta_md, salida)
    if not comp.correcta:
        raise ErrorInformePdf(
            f"El PDF no coincide con el .md: IDs que faltan {comp.ids_faltan}, IDs que sobran {comp.ids_sobran}, "
            f"números que faltan {comp.numeros_faltan}, números que sobran {comp.numeros_sobran}"
        )
    return salida


def _tokens(texto: str) -> tuple[Counter[str], Counter[str]]:
    """IDs C-xxx y números de un texto (los números se cuentan después de quitar los IDs)."""
    ids = Counter(_RE_ID.findall(texto))
    numeros = Counter(_RE_NUM.findall(_RE_ID.sub(" ", texto)))
    return ids, numeros


def _faltan(md: Counter[str], pdf: Counter[str]) -> list[str]:
    """Apariciones del .md que no están en el PDF (multiconjunto: cuenta repeticiones)."""
    return sorted((md - pdf).elements())


def _sobran(md: Counter[str], pdf: Counter[str]) -> list[str]:
    """Valores del PDF que no aparecen nunca en el .md."""
    return sorted(set(pdf) - set(md))


def texto_pdf(ruta_pdf: Path = INFORME_PDF) -> list[str]:
    """Texto extraído de cada página del PDF, sin el pie de página."""
    return [_RE_PIE.sub(" ", p.extract_text() or "") for p in PdfReader(ruta_pdf).pages]


def verificar_pdf(ruta_md: Path = INFORME, ruta_pdf: Path = INFORME_PDF) -> ComparacionPdf:
    """Compara IDs de cifra y números del PDF con los del .md: no puede faltar ninguno ni aparecer uno nuevo."""
    texto_md = ruta_md.read_text(encoding="utf-8")
    paginas = texto_pdf(ruta_pdf)
    ids_md, nums_md = _tokens(texto_md)
    ids_pdf, nums_pdf = _tokens("\n".join(paginas))
    paginas_cuerpo = next((i for i, p in enumerate(paginas) if "Anexo: cifras citadas" in p), len(paginas))
    return ComparacionPdf(
        paginas=len(paginas),
        paginas_cuerpo=paginas_cuerpo,
        ids_md=sum(ids_md.values()),
        numeros_md=sum(nums_md.values()),
        ids_faltan=_faltan(ids_md, ids_pdf),
        ids_sobran=_sobran(ids_md, ids_pdf),
        numeros_faltan=_faltan(nums_md, nums_pdf),
        numeros_sobran=_sobran(nums_md, nums_pdf),
    )
