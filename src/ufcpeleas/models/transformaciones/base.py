"""Utilidades comunes de las transformaciones: guardar la salida y registrarla en la bitácora."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.bitacora import Bitacora, EntradaBitacora


@dataclass
class Contexto:
    """Estado compartido por las transformaciones de una ejecución del pipeline."""

    bitacora: Bitacora = field(default_factory=Bitacora)
    #: Mensajes de control (cobertura, uniones no resueltas...) que se muestran al terminar.
    avisos: list[str] = field(default_factory=list)
    #: Salidas escritas en esta ejecución, en orden: (id transformación, ruta).
    salidas: list[tuple[str, Path]] = field(default_factory=list)

    def guardar(
        self,
        id_t: str,
        df: pd.DataFrame,
        ruta: Path,
        *,
        entrada: str,
        operacion: str,
        justificacion: str,
        filas_antes: int | str,
    ) -> pd.DataFrame:
        """Escribe `df` en `ruta` (interim/ o final/) y añade la fila correspondiente a la bitácora."""
        rutas.escribir_csv(df, ruta)
        self.salidas.append((id_t, ruta))
        self.bitacora.registrar(
            EntradaBitacora(
                id=id_t,
                entrada=entrada,
                operacion=operacion,
                justificacion=justificacion,
                filas_antes=filas_antes,
                filas_despues=len(df),
                salida=rutas.relativa(ruta),
            )
        )
        return df

    def avisar(self, mensaje: str) -> None:
        """Guarda un aviso de control para el resumen final."""
        self.avisos.append(mensaje)
