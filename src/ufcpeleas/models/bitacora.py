"""Bitácora: registro automático e idempotente de las transformaciones T-07+ del pipeline.

D-24: la columna `fecha` de las filas automáticas (T-07+) es la fecha de la última ejecución del pipeline;
coincide con la de las salidas en disco que recoge final/manifiesto_salidas.csv.

D-32: las filas manuales (T-00..T-06 y la serie I-01, I-02...) se conservan byte a byte. Orden estable del archivo:
primero todas las filas manuales en el orden en que aparecen en el archivo (T-00..T-06 y después las I-xx), y a
continuación las filas T-07+ que escribe el pipeline, en orden de ejecución.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ufcpeleas.models import rutas

COLUMNAS: tuple[str, ...] = (
    "id",
    "fecha",
    "responsable",
    "entrada",
    "operacion",
    "justificacion",
    "filas_antes",
    "filas_despues",
    "salida",
)

#: Primera transformación escrita por el pipeline; T-00..T-06 son manuales y no se tocan.
PRIMERA_T_PIPELINE: int = 7

_PATRON_ID = re.compile(r"^T-(\d+)$")
#: D-32: IDs de entradas manuales: T-00..T-06 e I-01, I-02...
_PATRON_MANUAL = re.compile(r"^(T-0[0-6]|I-\d{2,})$")


def es_fila_manual(id_t: str) -> bool:
    """True si el ID es de una entrada manual que el pipeline nunca modifica (D-32)."""
    return bool(_PATRON_MANUAL.match(id_t.strip()))


def es_fila_pipeline(id_t: str) -> bool:
    """True si el ID corresponde a una transformación del pipeline (T-07 en adelante)."""
    m = _PATRON_ID.match(id_t.strip())
    return bool(m) and int(m.group(1)) >= PRIMERA_T_PIPELINE


@dataclass
class EntradaBitacora:
    """Una fila de bitacora.csv."""

    id: str
    entrada: str
    operacion: str
    justificacion: str
    filas_antes: int | str
    filas_despues: int | str
    salida: str
    #: D-24: en las filas T-07+ la fecha es la de la última ejecución del pipeline (se regeneran en cada ejecución),
    #: no la del diseño de la transformación; T-00..T-06 son manuales y conservan su fecha.
    fecha: str = field(default_factory=lambda: date.today().isoformat())
    responsable: str = field(default_factory=lambda: rutas.RESPONSABLE)

    def como_fila(self) -> list[str]:
        """Valores en el orden de COLUMNAS."""
        return [str(getattr(self, c)) for c in COLUMNAS]


@dataclass
class Bitacora:
    """Acumula las entradas del pipeline y las escribe al final, conservando las manuales."""

    ruta: Path = field(default_factory=lambda: rutas.BITACORA)
    entradas: list[EntradaBitacora] = field(default_factory=list)

    def registrar(self, entrada: EntradaBitacora) -> None:
        """Añade una entrada; el ID debe ser T-07+ y no repetirse."""
        if not es_fila_pipeline(entrada.id):
            raise ValueError(f"El pipeline solo escribe T-{PRIMERA_T_PIPELINE:02d}+: {entrada.id}")
        if any(e.id == entrada.id for e in self.entradas):
            raise ValueError(f"ID repetido en la bitácora: {entrada.id}")
        self.entradas.append(entrada)

    def escribir(self) -> Path:
        """Reescribe bitacora.csv: conserva literalmente las filas manuales y sustituye las T-07+."""
        # Lectura en bytes: se respetan los finales de línea originales (hay filas manuales con CRLF).
        texto = self.ruta.read_bytes().decode("utf-8") if self.ruta.exists() else ""
        conservado = conservar_filas_manuales(texto)
        buf = io.StringIO()
        escritor = csv.writer(buf, lineterminator="\n")
        if not conservado:
            escritor.writerow(COLUMNAS)
        for e in self.entradas:
            escritor.writerow(e.como_fila())
        rutas.comprobar_escritura(self.ruta)
        self.ruta.write_bytes((conservado + buf.getvalue()).encode("utf-8"))
        return self.ruta


def conservar_filas_manuales(texto: str) -> str:
    """Devuelve la cabecera y las filas no generadas por el pipeline, con su texto original exacto."""
    if not texto:
        return ""
    # Se trocea solo por "\n" y se pasa la lista al lector csv, para que line_num y los trozos coincidan.
    lineas = re.findall(r"[^\n]*\n|[^\n]+$", texto)
    lector = csv.reader(lineas)
    cabecera = next(lector)
    if tuple(cabecera) != COLUMNAS:
        raise ValueError(f"Cabecera de bitácora inesperada: {cabecera}")
    partes = ["".join(lineas[: lector.line_num])]
    fin_anterior = lector.line_num
    for registro in lector:
        fin = lector.line_num
        if registro and not es_fila_pipeline(registro[0]):
            if not es_fila_manual(registro[0]):
                raise ValueError(f"ID de bitácora no reconocido (D-32 admite T-00..T-06, I-xx y T-07+): {registro[0]}")
            trozo = "".join(lineas[fin_anterior:fin])
            partes.append(trozo if trozo.endswith("\n") else trozo + "\n")
        fin_anterior = fin
    return "".join(partes)


def leer_bitacora(ruta: Path | None = None) -> list[dict[str, str]]:
    """Lee bitacora.csv como lista de diccionarios."""
    with open(ruta or rutas.BITACORA, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
