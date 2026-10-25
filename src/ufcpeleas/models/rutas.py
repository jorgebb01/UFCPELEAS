"""Rutas del proyecto, constantes de trazabilidad y guardas de escritura."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

#: Raíz del repositorio (src/ufcpeleas/models/rutas.py -> parents[3]); se puede sobrescribir con UFCPELEAS_ROOT.
RAIZ: Path = Path(os.environ.get("UFCPELEAS_ROOT", Path(__file__).resolve().parents[3]))

RAW: Path = RAIZ / "raw"
MANUAL: Path = RAIZ / "manual"
INTERIM: Path = RAIZ / "interim"
FINAL: Path = RAIZ / "final"

REGISTRO_FUENTES: Path = RAIZ / "registro_fuentes.csv"
BITACORA: Path = RAIZ / "bitacora.csv"
DICCIONARIO: Path = RAIZ / "diccionario.csv"

#: Responsable de las filas que escribe el pipeline (configurable sin tocar el código).
RESPONSABLE: str = os.environ.get("UFCPELEAS_RESPONSABLE", "jorgebb01")

#: Directorios en los que el código puede escribir. raw/ y manual/ son de solo lectura.
_ESCRITURA_PERMITIDA: tuple[Path, ...] = (INTERIM, FINAL)
_ARCHIVOS_RAIZ_PERMITIDOS: tuple[Path, ...] = (BITACORA, DICCIONARIO)


def relativa(ruta: Path) -> str:
    """Ruta relativa a la raíz del repositorio, con separador '/'."""
    return Path(ruta).resolve().relative_to(RAIZ.resolve()).as_posix()


def comprobar_escritura(ruta: Path) -> Path:
    """Aborta si `ruta` no está en interim/, final/ o es bitacora.csv / diccionario.csv."""
    r = Path(ruta).resolve()
    if r in [p.resolve() for p in _ARCHIVOS_RAIZ_PERMITIDOS]:
        return r
    for base in _ESCRITURA_PERMITIDA:
        if r.is_relative_to(base.resolve()):
            return r
    raise PermissionError(f"Escritura prohibida fuera de interim/ y final/: {r}")


def escribir_csv(df: pd.DataFrame, ruta: Path) -> Path:
    """Escribe un CSV (UTF-8, sin índice, fin de línea '\\n') respetando las guardas de escritura."""
    r = comprobar_escritura(ruta)
    r.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(r, index=False, lineterminator="\n")
    return r
