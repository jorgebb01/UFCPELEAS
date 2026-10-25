"""Orquestación del pipeline: paso 0 (hashes) y transformaciones T-07+ desde raw/ y manual/."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.diccionario import escribir_diccionario
from ufcpeleas.models.fuentes import Verificacion, sha256, verificar_fuentes
from ufcpeleas.models.transformaciones import cuotas, dataset, peleas
from ufcpeleas.models.transformaciones.base import Contexto


@dataclass
class ResultadoPipeline:
    """Resumen de una ejecución del pipeline."""

    verificaciones: list[Verificacion]
    contexto: Contexto
    final: pd.DataFrame
    cobertura: pd.DataFrame
    peleas_clave: pd.DataFrame


def paso0_verificar() -> list[Verificacion]:
    """Paso 0: verifica las fuentes de registro_fuentes.csv y guarda el resultado en final/verificacion_fuentes.csv."""
    verificaciones = verificar_fuentes()
    tabla = pd.DataFrame(
        [
            {
                "id_fuente": v.id_fuente,
                "ruta": v.ruta,
                "sha256": v.sha256_disco,
                "bytes": v.bytes_disco,
                "filas": v.filas_disco,
                "correcta": v.correcta,
            }
            for v in verificaciones
        ]
    )
    rutas.escribir_csv(tabla, rutas.FINAL / "verificacion_fuentes.csv")
    return verificaciones


def ejecutar() -> ResultadoPipeline:
    """Ejecuta el pipeline completo; aborta antes de transformar si algún hash no coincide."""
    verificaciones = paso0_verificar()
    ctx = Contexto()
    t07 = peleas.t07_peleas(ctx)
    t08 = peleas.t08_resultados(ctx, t07)
    t09 = peleas.t09_perspectivas(ctx, t08)
    t10 = peleas.t10_historial(ctx, t09)
    t11 = peleas.t11_historial_rival(ctx, t10)
    t12 = cuotas.t12_union_f04_f01(ctx, t08)
    t13 = cuotas.t13_f05_moneyline(ctx)
    t14 = cuotas.t14_f05_probabilidades(ctx, t13, t12)
    t15 = cuotas.t15_f07_filtro(ctx)
    t16 = cuotas.t16_f07_cierre_por_casa(ctx, t15, t08)
    t17 = cuotas.t17_f02_manual(ctx, t08)
    t18 = cuotas.t18_cuotas_consolidadas(ctx, t08, t14, t16, t17)
    final = dataset.t19_dataset_final(ctx, t11, t18)
    cobertura = dataset.t20_cobertura(ctx, final)
    clave = dataset.t21_peleas_clave(ctx, final)
    ctx.bitacora.escribir()
    escribir_diccionario(final)
    _escribir_manifiesto(ctx)
    return ResultadoPipeline(verificaciones, ctx, final, cobertura, clave)


def _escribir_manifiesto(ctx: Contexto) -> None:
    """Guarda el SHA-256 de cada salida del pipeline (final/manifiesto_salidas.csv) para verificar la reproducibilidad."""
    filas = [
        {"id_transformacion": t, "archivo": rutas.relativa(r), "sha256": sha256(r), "bytes": r.stat().st_size}
        for t, r in ctx.salidas
    ]
    for extra in (rutas.DICCIONARIO,):
        filas.append({"id_transformacion": "", "archivo": rutas.relativa(extra), "sha256": sha256(extra), "bytes": extra.stat().st_size})
    rutas.escribir_csv(pd.DataFrame(filas), rutas.FINAL / "manifiesto_salidas.csv")
