"""Informe ejecutivo: rellena docs/informe_plantilla.md con las cifras de final/cifras.csv (cada número lleva su ID C-xxx)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.cifras import CIFRAS, LINAJE, cifras_afectadas

PLANTILLA: Path = rutas.RAIZ / "docs" / "informe_plantilla.md"
INFORME: Path = rutas.FINAL / "informe_ejecutivo.md"
DECISIONES: Path = rutas.RAIZ / "decisiones.md"

#: Marcadores de la plantilla: {{C-049:pct}}, {{DIF:C-058-C-049:pp}}, {{LINAJE:T-07}}, {{NCIFRAS}}, {{NDEC}}.
_MARCADOR = re.compile(r"\{\{([^{}]+)\}\}")


class ErrorInforme(Exception):
    """La plantilla cita una cifra o un formato que no existe."""


def _num(x: float, decimales: int) -> str:
    """Número con coma decimal (convención española)."""
    return f"{x:.{decimales}f}".replace(".", ",")


def formatear(valor: object, formato: str) -> str:
    """Aplica un formato de la plantilla: pct (fracción), pctv (valor ya en %), pp, dec1, dec3, dec4, int o raw."""
    if formato == "raw":
        return str(valor)
    x = float(valor)
    if formato == "pct":
        return f"{_num(x * 100, 1)} %"
    if formato == "pctv":
        return f"{_num(x, 1)} %"
    if formato == "pp":
        return _num(x * 100, 1)
    if formato == "dec1":
        return _num(x, 1)
    if formato == "dec3":
        return _num(x, 3)
    if formato == "dec4":
        return _num(x, 4)
    if formato == "int":
        return str(int(round(x)))
    raise ErrorInforme(f"Formato desconocido: {formato}")


def _valor(cifras: pd.DataFrame, id_cifra: str) -> object:
    fila = cifras.loc[cifras["id_cifra"] == id_cifra, "valor"]
    if fila.empty:
        raise ErrorInforme(f"La plantilla cita {id_cifra}, que no está en {rutas.relativa(CIFRAS)}")
    return fila.iloc[0]


def renderizar(plantilla: str, cifras: pd.DataFrame, ruta_linaje: str | None = None) -> tuple[str, list[str]]:
    """Sustituye los marcadores y devuelve el texto y la lista ordenada de cifras citadas."""
    citadas: list[str] = []
    n_decisiones = len(re.findall(r"^## D-\d+", DECISIONES.read_text(encoding="utf-8"), flags=re.M))

    def sustituir(m: re.Match[str]) -> str:
        partes = m.group(1).split(":")
        clave = partes[0]
        if clave == "NCIFRAS":
            return str(len(cifras))
        if clave == "NDEC":
            return str(n_decisiones)
        if clave == "LINAJE":
            return str(len(cifras_afectadas(partes[1], ruta_linaje=ruta_linaje)))
        if clave == "DIF":
            a, b = re.fullmatch(r"(C-\d{3})-(C-\d{3})", partes[1]).groups()  # type: ignore[union-attr]
            citadas.extend([a, b])
            return f"{formatear(float(_valor(cifras, a)) - float(_valor(cifras, b)), partes[2])} [{a} − {b}]"
        if re.fullmatch(r"C-\d{3}", clave):
            citadas.append(clave)
            texto = formatear(_valor(cifras, clave), partes[1] if len(partes) > 1 else "raw")
            return f"{texto} [{clave}]"
        raise ErrorInforme(f"Marcador desconocido: {m.group(0)}")

    texto = _MARCADOR.sub(sustituir, plantilla)
    return texto, list(dict.fromkeys(citadas))


def _anexo(cifras: pd.DataFrame, citadas: list[str]) -> str:
    """Tabla de las cifras citadas con su archivo, localizador y transformación (ruta de vuelta del auditor)."""
    filas = ["", "## Anexo: cifras citadas", "", "| ID | Valor | Descripción | Archivo | Localizador | Transformación |", "|---|---|---|---|---|---|"]
    for c in cifras[cifras["id_cifra"].isin(citadas)].itertuples():
        filas.append(f"| {c.id_cifra} | {c.valor} | {c.descripcion} | `{c.archivo}` | {c.localizador} | {c.transformacion} |")
    return "\n".join(filas) + "\n"


def generar(ruta_plantilla: Path = PLANTILLA, ruta_salida: Path = INFORME) -> Path:
    """Genera final/informe_ejecutivo.md a partir de la plantilla y de final/cifras.csv."""
    cifras = pd.read_csv(CIFRAS, dtype={"valor": str})
    texto, citadas = renderizar(ruta_plantilla.read_text(encoding="utf-8"), cifras, ruta_linaje=str(LINAJE))
    salida = rutas.comprobar_escritura(ruta_salida)
    salida.write_text(texto.rstrip("\n") + "\n" + _anexo(cifras, citadas), encoding="utf-8", newline="\n")
    return salida
