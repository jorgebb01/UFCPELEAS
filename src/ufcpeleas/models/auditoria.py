"""Auditoría de solo lectura: de una cifra (C-xxx) a su fila en final/interim, su bitácora, su linaje y la fila cruda de raw/manual.

Este módulo no importa Flask ni escribe en disco: lo usan los controladores de la app del simulacro de auditoría.
"""

from __future__ import annotations

import csv
import io
import math
import random
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable

import markdown
import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.bitacora import leer_bitacora
from ufcpeleas.models.cifras import CIFRAS, LINAJE, cifras_afectadas
from ufcpeleas.models.fuentes import leer_registro_fuentes, verificar_fuentes
from ufcpeleas.models.informe import DECISIONES, INFORME

#: Salidas que necesita la app; si falta alguna hay que ejecutar el pipeline.
SALIDAS_NECESARIAS: tuple[Path, ...] = (CIFRAS, LINAJE, rutas.FINAL / "escenarios.csv", INFORME, rutas.BITACORA)
#: Filas por página en las listas largas.
POR_PAGINA = 25

_ID_CIFRA = re.compile(r"^C-\d{3}$")
_NODO = re.compile(r"^(T-\d{2}|F-\d{2}|I-\d{2})$")
_PATRON_D = re.compile(r"\bD-\d{2}\b")


class SalidasAusentes(RuntimeError):
    """Faltan salidas del pipeline en final/ (hay que ejecutar `uv run ufcpeleas pipeline`)."""


def salidas_faltantes() -> list[str]:
    """Rutas relativas de las salidas necesarias que no existen."""
    return [rutas.relativa(p) for p in SALIDAS_NECESARIAS if not p.exists()]


def _firma(ruta: Path) -> tuple[str, float, int]:
    """Clave de caché: ruta, fecha de modificación y tamaño (si el pipeline regenera el archivo, se relee)."""
    st = ruta.stat()
    return str(ruta), st.st_mtime, st.st_size


@lru_cache(maxsize=32)
def _leer_tabla(ruta: str, _mtime: float, _tam: int) -> pd.DataFrame:
    """CSV como texto, sin convertir tipos, para mostrar los valores tal como están en el archivo."""
    return pd.read_csv(ruta, dtype=str, keep_default_na=False)


def tabla(ruta: Path) -> pd.DataFrame:
    """Tabla en caché de un CSV del proyecto."""
    return _leer_tabla(*_firma(ruta))


# --------------------------------------------------------------------------- cifras


def lista_cifras() -> pd.DataFrame:
    """Todas las cifras de final/cifras.csv."""
    return tabla(CIFRAS)


def cifra(id_cifra: str) -> dict[str, str] | None:
    """Fila de final/cifras.csv o None si el ID no existe."""
    if not _ID_CIFRA.match(id_cifra):
        return None
    c = lista_cifras()
    fila = c[c["id_cifra"] == id_cifra]
    return None if fila.empty else fila.iloc[0].to_dict()


def cifra_al_azar(rng: random.Random | None = None) -> str:
    """ID de una cifra elegida al azar (para el simulacro; no afecta a ninguna cifra del informe)."""
    return (rng or random.SystemRandom()).choice(list(lista_cifras()["id_cifra"]))


def ruta_segura(relativa: str) -> Path | None:
    """Ruta dentro de interim/ o final/ (o None): evita leer fuera de las salidas del pipeline."""
    p = (rutas.RAIZ / relativa).resolve()
    for base in (rutas.INTERIM, rutas.FINAL):
        if p.is_relative_to(base.resolve()) and p.suffix == ".csv" and p.exists():
            return p
    return None


@dataclass
class Localizacion:
    """Filas del archivo de la cifra que cumplen el localizador."""

    archivo: str
    filtros: list[tuple[str, str]]
    columna: str | None
    columnas: list[str]
    filas: list[dict[str, str]]
    coincide: bool | None
    error: str = ""


def parsear_localizador(texto: str) -> tuple[list[tuple[str, str]], str | None]:
    """Convierte "a = x, b = y, columna z" en ([(a, x), (b, y)], z). Admite "columna z = v" como filtro sobre z."""
    columna = None
    m = re.search(r"(?:^|, )columna (\w+)(?: = (.+))?$", texto)
    resto = texto
    filtros: list[tuple[str, str]] = []
    if m:
        columna = m.group(1)
        if m.group(2) is not None:
            filtros.append((columna, m.group(2)))
        resto = texto[: m.start()]
    for k, v in re.findall(r"(\w+) = (.+?)(?=, \w+ = |$)", resto):
        filtros.append((k, v))
    return filtros, columna


def _igual(a: str, b: str) -> bool:
    """Compara dos valores como número (6 decimales) o como texto."""
    try:
        x, y = float(a), float(b)
        return math.isclose(round(x, 6), round(y, 6), abs_tol=1e-9)
    except ValueError:
        return a == b


def localizar(c: dict[str, str]) -> Localizacion:
    """Filas del archivo de la cifra según su localizador y comprobación de que el valor coincide."""
    ruta = ruta_segura(c["archivo"])
    filtros, columna = parsear_localizador(c["localizador"])
    if ruta is None:
        return Localizacion(c["archivo"], filtros, columna, [], [], None, "archivo no disponible")
    df = tabla(ruta)
    sel = df
    for k, v in filtros:
        if k not in sel.columns:
            return Localizacion(c["archivo"], filtros, columna, list(df.columns), [], None, f"columna {k} no existe")
        sel = sel[sel[k] == v]
    filas = sel.head(POR_PAGINA).to_dict("records")
    coincide = None
    if columna and any(k == columna for k, _ in filtros) and len(sel) >= 1:
        # "columna elegido = True": la columna es el filtro; el valor de la cifra está en otra celda de la fila.
        coincide = all(any(_igual(x, c["valor"]) for x in fila) for _, fila in sel.iterrows())
    elif columna and columna in sel.columns and len(sel) >= 1:
        coincide = all(_igual(x, c["valor"]) for x in sel[columna])
    elif len(sel) == 1:
        coincide = any(_igual(x, c["valor"]) for x in sel.iloc[0])
    return Localizacion(c["archivo"], filtros, columna, list(df.columns), filas, coincide)


# --------------------------------------------------------------------------- filas crudas


@dataclass
class FilaCruda:
    """Registro exacto de un archivo de raw/ o manual/."""

    id_fuente: str
    archivo: str
    source_row: int
    source_line: int
    campos: dict[str, str]
    extra: dict[str, str] = field(default_factory=dict)


@lru_cache(maxsize=16)
def _indice_registros(ruta: str, _mtime: float, _tam: int) -> tuple[list[str], list[int], list[int]]:
    """Cabecera, línea física inicial de cada registro (más un centinela) y desplazamiento en bytes de cada línea.

    Se trocea solo por "\n" (como fuentes.lineas_de_registros) para que el número de línea física coincida.
    """
    with open(ruta, "rb") as fh:
        datos = fh.read()
    desplazamientos = [0] + [m.end() for m in re.finditer(b"\n", datos)]
    if desplazamientos[-1] == len(datos):
        desplazamientos.pop()  # el archivo termina en salto de línea: no hay línea vacía final
    fines = desplazamientos[1:] + [len(datos)]
    lector = csv.reader(datos[a:b].decode("utf-8") for a, b in zip(desplazamientos, fines))
    cabecera = next(lector)
    inicios: list[int] = []
    fin = lector.line_num
    for _ in lector:
        inicios.append(fin + 1)
        fin = lector.line_num
    inicios.append(fin + 1)  # centinela: línea siguiente al último registro
    desplazamientos.append(len(datos))
    return cabecera, inicios, desplazamientos


def ruta_fuente(id_fuente: str) -> Path | None:
    """Ruta del archivo de una fuente de registro_fuentes.csv."""
    reg = leer_registro_fuentes().set_index("id_fuente")
    return rutas.RAIZ / reg.loc[id_fuente, "ruta"] if id_fuente in reg.index else None


def fila_cruda(id_fuente: str, source_row: int) -> FilaCruda | None:
    """Lee el registro `source_row` (1 = primer registro tras la cabecera) del archivo original, sin modificarlo."""
    ruta = ruta_fuente(id_fuente)
    if ruta is None or not ruta.exists():
        return None
    cabecera, inicios, desp = _indice_registros(*_firma(ruta))
    if not 1 <= source_row < len(inicios):
        return None
    linea = inicios[source_row - 1]
    a, b = desp[linea - 1], desp[inicios[source_row] - 1]
    with open(ruta, "rb") as fh:
        fh.seek(a)
        texto = fh.read(b - a).decode("utf-8")
    valores = next(csv.reader(io.StringIO(texto, newline="")))
    return FilaCruda(id_fuente, rutas.relativa(ruta), source_row, linea, dict(zip(cabecera, valores)))


def _por_id_manual(id_manual: str) -> FilaCruda | None:
    """Fila de F-02 (cuotas) o F-08 (resultados verificados) por id_manual, con su captura de F-03."""
    for f in ("F-02", "F-08"):
        ruta = ruta_fuente(f)
        df = tabla(ruta)
        pos = df.index[df["id_manual"] == id_manual]
        if len(pos):
            fila = fila_cruda(f, int(pos[0]) + 1)
            if fila:
                fila.extra = captura_de(fila.campos.get("url", ""))
            return fila
    return None


def captura_de(url: str) -> dict[str, str]:
    """Captura de manual/capturas/ cuya URL coincide con la de la fila (archivo, fecha y SHA-256 del índice F-03)."""
    if not url:
        return {}
    indice = tabla(ruta_fuente("F-03"))
    limpia = url.rstrip("/")
    m = indice[indice["url"].str.rstrip("/") == limpia]
    if m.empty:
        return {"url": url}
    c = m.iloc[0]
    return {"url": url, "captura": c["archivo"], "fecha_captura_utc": c["fecha_captura_utc"], "sha256": c["sha256"]}


@dataclass
class Origen:
    """Referencias de la columna `origen` de una cifra, agrupadas por fuente."""

    filas: dict[str, list[int]]
    ids_manuales: list[str]
    tablas: list[str]
    texto: str


def parsear_origen(texto: str) -> Origen:
    """Extrae source_row de F-01, filas de F-05/F-07, id_manual (M-xxxx) y tablas interim/final citadas."""
    filas: dict[str, list[int]] = {}
    for nums in re.findall(r"F-01 source_row ([\d;]+)", texto):
        filas.setdefault("F-01", []).extend(int(x) for x in nums.split(";") if x)
    for f, nums in re.findall(r"(F-0[57]):([\d;]+)", texto):
        filas.setdefault(f, []).extend(int(x) for x in nums.split(";") if x)
    filas = {k: list(dict.fromkeys(v)) for k, v in filas.items()}
    ids = list(dict.fromkeys(re.findall(r"M-\d{4}", texto)))
    tablas = list(dict.fromkeys(re.findall(r"(?:interim|final)/[\w.-]+\.csv", texto)))
    return Origen(filas, ids, tablas, texto)


@dataclass
class OrigenResuelto:
    """Filas crudas de una página del origen de una cifra."""

    origen: Origen
    crudas: list[FilaCruda]
    total: int
    pagina: int
    paginas: int


def resolver_origen(c: dict[str, str], pagina: int = 1) -> OrigenResuelto:
    """Lee del archivo original las filas citadas en `origen`, paginadas de POR_PAGINA en POR_PAGINA."""
    o = parsear_origen(c["origen"])
    # Primero las filas de cuotas (F-05, F-07, M-xxxx), que son las más específicas; después las peleas de F-01.
    orden = sorted(o.filas.items(), key=lambda kv: kv[0] == "F-01")
    refs: list[tuple[str, object]] = [(f, n) for f, ns in orden if f != "F-01" for n in ns] + [("M", i) for i in o.ids_manuales]
    refs += [("F-01", n) for n in o.filas.get("F-01", [])]
    total = len(refs)
    paginas = max(1, math.ceil(total / POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    crudas = []
    for f, ref in refs[(pagina - 1) * POR_PAGINA : pagina * POR_PAGINA]:
        fila = _por_id_manual(str(ref)) if f == "M" else fila_cruda(f, int(ref))
        if fila:
            crudas.append(fila)
    return OrigenResuelto(o, crudas, total, pagina, paginas)


# --------------------------------------------------------------------------- bitácora, decisiones, linaje


def bitacora() -> list[dict[str, str]]:
    """Filas de bitacora.csv con las decisiones citadas en la justificación."""
    filas = leer_bitacora()
    for f in filas:
        f["decisiones"] = sorted(set(_PATRON_D.findall(f["justificacion"] + " " + f["operacion"])))
    return filas


def fila_bitacora(id_t: str) -> dict[str, str] | None:
    """Fila de la bitácora de una transformación."""
    return next((f for f in bitacora() if f["id"] == id_t), None)


def decisiones_html() -> tuple[str, list[str]]:
    """decisiones.md en HTML, con un ancla id="D-xx" por decisión, y la lista de IDs."""
    texto = DECISIONES.read_text(encoding="utf-8")
    ids = re.findall(r"^## (D-\d{2})", texto, flags=re.M)
    texto = re.sub(r"^## (D-\d{2})", r'<a id="\1"></a>\n\n## \1', texto, flags=re.M)
    return markdown.markdown(texto, extensions=["tables"]), ids


def linaje_de(id_cifra: str) -> dict[str, list[str]]:
    """Transformación directa, transformaciones previas y fuentes de una cifra (final/linaje.csv)."""
    lin = tabla(LINAJE)
    g = lin[lin["id_cifra"] == id_cifra]
    return {t: list(g.loc[g["tipo"] == t, "nodo"]) for t in ("transformacion_directa", "transformacion_previa", "fuente")}


def es_nodo(nodo: str) -> bool:
    """True si `nodo` es un ID de transformación o de fuente con formato válido."""
    return bool(_NODO.match(nodo))


def afectadas(nodo: str) -> pd.DataFrame:
    """Cifras que cambian si `nodo` (T-xx o F-xx) tiene un error (pregunta 4)."""
    return cifras_afectadas(nodo, ruta_linaje=str(LINAJE), ruta_cifras=str(CIFRAS))


# --------------------------------------------------------------------------- portada, informe, fuentes


def escenarios() -> list[dict[str, str]]:
    """Filas de final/escenarios.csv."""
    return tabla(rutas.FINAL / "escenarios.csv").to_dict("records")


def informe_html(enlace: Callable[[str], str]) -> str:
    """final/informe_ejecutivo.md en HTML; cada [C-xxx] (o [C-xxx − C-yyy]) enlaza con `enlace(id)`."""
    html = markdown.markdown(INFORME.read_text(encoding="utf-8"), extensions=["tables"])

    def sustituir(m: re.Match[str]) -> str:
        return re.sub(r"C-\d{3}", lambda x: f'<a class="cifra" href="{enlace(x.group(0))}">{x.group(0)}</a>', m.group(0))

    html = re.sub(r"\[C-\d{3}(?: − C-\d{3})?\]", sustituir, html)
    # Celdas de la tabla del anexo: el ID va solo en la primera columna.
    return re.sub(r"<td>(C-\d{3})</td>", lambda m: f'<td><a class="cifra" href="{enlace(m.group(1))}">{m.group(1)}</a></td>', html)


@dataclass
class EstadoFuente:
    """Fuente registrada y resultado de la verificación en vivo."""

    registro: dict[str, str]
    sha256_disco: str
    bytes_disco: int
    filas_disco: int
    correcta: bool


def estado_fuentes() -> tuple[list[EstadoFuente], list[dict[str, object]], str]:
    """Paso 0 en vivo, sin escribir nada: registro de fuentes, capturas de F-03 y mensaje de error si lo hay."""
    registro = leer_registro_fuentes()
    try:
        verifs = verificar_fuentes()
        error = ""
    except Exception as e:  # noqa: BLE001 - se muestra en la página
        return [], [], str(e)
    por_id = {v.id_fuente: v for v in verifs if v.id_fuente != "F-03/captura"}
    estados = [
        EstadoFuente(r, por_id[r["id_fuente"]].sha256_disco, por_id[r["id_fuente"]].bytes_disco, por_id[r["id_fuente"]].filas_disco, por_id[r["id_fuente"]].correcta)
        for r in registro.to_dict("records")
    ]
    capturas = [
        {"ruta": v.ruta, "sha256": v.sha256_disco, "bytes": v.bytes_disco, "correcta": v.correcta}
        for v in verifs
        if v.id_fuente == "F-03/captura"
    ]
    return estados, capturas, error


def ruta_captura(nombre: str) -> Path | None:
    """Ruta de una captura listada en el índice F-03 (solo nombres del índice)."""
    indice = tabla(ruta_fuente("F-03"))
    if nombre not in set(indice["archivo"]):
        return None
    p = rutas.MANUAL / "capturas" / nombre
    return p if p.exists() else None


def pagina_tabla(ruta: Path, pagina: int) -> tuple[list[str], list[dict[str, str]], int, int, int]:
    """Columnas, filas de la página, total, página y número de páginas de un CSV de interim/ o final/."""
    df = tabla(ruta)
    paginas = max(1, math.ceil(len(df) / POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    return list(df.columns), df.iloc[(pagina - 1) * POR_PAGINA : pagina * POR_PAGINA].to_dict("records"), len(df), pagina, paginas
