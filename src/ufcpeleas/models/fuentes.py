"""Fuentes: verificación de hashes (paso 0) y carga de archivos con identificadores de origen."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ufcpeleas.models import rutas

#: Columnas de origen que se añaden a cada fila leída de una fuente.
COLUMNAS_ORIGEN: tuple[str, ...] = ("source_id", "source_file", "source_row", "source_line")


class ErrorVerificacion(RuntimeError):
    """Una fuente registrada no coincide con el archivo en disco (hash, bytes o filas)."""


@dataclass(frozen=True)
class Verificacion:
    """Resultado de verificar un archivo registrado."""

    id_fuente: str
    ruta: str
    sha256_registro: str
    sha256_disco: str
    bytes_registro: int
    bytes_disco: int
    filas_registro: int
    filas_disco: int

    @property
    def correcta(self) -> bool:
        """True si hash, tamaño y número de registros coinciden."""
        return (
            self.sha256_registro == self.sha256_disco
            and self.bytes_registro == self.bytes_disco
            and self.filas_registro == self.filas_disco
        )


def sha256(ruta: Path) -> str:
    """SHA-256 hexadecimal de un archivo, leído por bloques."""
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def lineas_de_registros(ruta: Path) -> list[int]:
    """Línea física (1 = cabecera) en la que empieza cada registro de datos de un CSV.

    Un registro puede ocupar varias líneas físicas (campos entre comillas con saltos de
    línea, p. ej. `result_details` en F-01), por eso se cuentan registros y no líneas.
    """
    inicios: list[int] = []
    with open(ruta, newline="", encoding="utf-8") as fh:
        lector = csv.reader(fh)
        next(lector)
        fin_anterior = lector.line_num
        for _ in lector:
            inicios.append(fin_anterior + 1)
            fin_anterior = lector.line_num
    return inicios


def contar_registros(ruta: Path) -> int:
    """Número de registros de datos de un CSV (sin la cabecera)."""
    return len(lineas_de_registros(ruta))


def leer_registro_fuentes(ruta: Path | None = None) -> pd.DataFrame:
    """Lee registro_fuentes.csv como texto."""
    return pd.read_csv(ruta or rutas.REGISTRO_FUENTES, dtype=str, keep_default_na=False)


def verificar_fuentes(ruta_registro: Path | None = None, raiz: Path | None = None) -> list[Verificacion]:
    """Paso 0: compara SHA-256, bytes y registros de cada fuente con el disco; aborta si algo difiere.

    Además verifica el SHA-256 y el tamaño de cada captura listada en el índice F-03.
    """
    raiz = raiz or rutas.RAIZ
    registro = leer_registro_fuentes(ruta_registro)
    resultados: list[Verificacion] = []
    for fila in registro.itertuples(index=False):
        archivo = raiz / fila.ruta
        if not archivo.exists():
            raise ErrorVerificacion(f"{fila.id_fuente}: no existe {fila.ruta}")
        resultados.append(
            Verificacion(
                id_fuente=fila.id_fuente,
                ruta=fila.ruta,
                sha256_registro=fila.sha256,
                sha256_disco=sha256(archivo),
                bytes_registro=int(fila.bytes),
                bytes_disco=archivo.stat().st_size,
                filas_registro=int(fila.filas),
                filas_disco=contar_registros(archivo),
            )
        )
        if fila.id_fuente == "F-03":
            resultados.extend(_verificar_capturas(archivo))
    fallos = [v for v in resultados if not v.correcta]
    if fallos:
        detalle = "; ".join(
            f"{v.id_fuente} {v.ruta} (sha {v.sha256_disco[:12]}… vs {v.sha256_registro[:12]}…, "
            f"bytes {v.bytes_disco} vs {v.bytes_registro}, filas {v.filas_disco} vs {v.filas_registro})"
            for v in fallos
        )
        raise ErrorVerificacion(f"Verificación de fuentes fallida: {detalle}")
    return resultados


def _verificar_capturas(indice: Path) -> list[Verificacion]:
    """Verifica cada captura HTML del índice F-03 (hash y bytes; las filas no aplican)."""
    tabla = pd.read_csv(indice, dtype=str, keep_default_na=False)
    salida: list[Verificacion] = []
    for fila in tabla.itertuples(index=False):
        archivo = indice.parent / fila.archivo
        if not archivo.exists():
            raise ErrorVerificacion(f"F-03: no existe la captura {fila.archivo}")
        salida.append(
            Verificacion(
                id_fuente="F-03/captura",
                ruta=rutas.relativa(archivo) if archivo.resolve().is_relative_to(rutas.RAIZ.resolve()) else str(archivo),
                sha256_registro=fila.sha256,
                sha256_disco=sha256(archivo),
                bytes_registro=int(fila.bytes),
                bytes_disco=archivo.stat().st_size,
                filas_registro=0,
                filas_disco=0,
            )
        )
    return salida


def leer_fuente(id_fuente: str, **kwargs) -> pd.DataFrame:
    """Lee una fuente registrada y añade source_id, source_file, source_row y source_line.

    `source_row` es el número de registro de datos (1 = primer registro tras la cabecera);
    `source_line` es la línea física donde empieza ese registro (la cabecera es la línea 1).
    """
    registro = leer_registro_fuentes().set_index("id_fuente")
    ruta_rel = registro.loc[id_fuente, "ruta"]
    ruta = rutas.RAIZ / ruta_rel
    df = pd.read_csv(ruta, low_memory=False, **kwargs)
    lineas = lineas_de_registros(ruta)
    if len(lineas) != len(df):
        raise ErrorVerificacion(f"{id_fuente}: pandas lee {len(df)} filas y csv {len(lineas)} registros")
    origen = pd.DataFrame(
        {
            "source_id": id_fuente,
            "source_file": ruta_rel,
            "source_row": range(1, len(df) + 1),
            "source_line": lineas,
        }
    )
    return pd.concat([origen, df.reset_index(drop=True)], axis=1)
