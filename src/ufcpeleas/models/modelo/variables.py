"""Variables del modelo de probabilidad: diferencias peleador - rival (antisimétricas) y logit de la cuota."""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Fecha de inicio del entrenamiento (D-18, condición 2).
INICIO_ENTRENAMIENTO = "2021-01-01"
#: Inicio del periodo de evaluación (test temporal). D-27.
INICIO_TEST = "2025-01-01"
#: Inicio del periodo de validación para elegir la regularización (dentro del entrenamiento). D-27.
INICIO_VALIDACION = "2024-01-01"

#: Variables de historial y físicas que entran como diferencia peleador - rival (todas previas a la pelea: D-03, D-23).
VARIABLES_DIFERENCIA: tuple[str, ...] = (
    "hist_peleas",
    "hist_victorias",
    "hist_derrotas",
    "hist_pct_victorias",
    "hist_racha",
    "hist_victorias_ko",
    "hist_derrotas_ko",
    "hist_peleas_titulo",
    "hist_dias_desde_ultima",
    "hist_peleas_365d",
    "hist_minutos",
    "hist_sig_conectados_min",
    "hist_sig_recibidos_min",
    "hist_sig_precision",
    "hist_sig_defensa",
    "hist_derribos_15min",
    "hist_derribos_precision",
    "hist_derribos_defensa",
    "hist_knockdowns_15min",
    "hist_knockdowns_recibidos_15min",
    "hist_sumision_intentos_15min",
    "hist_control_pct",
    "edad",
    "altura_cm",
    "alcance_cm",
)

#: Indicadores de dato ausente, también como diferencia (peleador - rival) para conservar la antisimetría.
INDICADORES: tuple[str, ...] = ("debut", "sin_edad", "sin_alcance", "sin_estadisticas")

#: Límite para el logit de la probabilidad de mercado.
_EPS = 0.01


def columnas_historial() -> list[str]:
    """Nombres de las variables del modelo sin cuota (modelo B)."""
    return [f"d_{v}" for v in VARIABLES_DIFERENCIA] + [f"d_{i}" for i in INDICADORES]


def columnas_combinado() -> list[str]:
    """Nombres de las variables del modelo con cuota + historial (modelo C)."""
    return ["logit_mercado", *columnas_historial()]


def construir_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula las variables del modelo para filas con columnas del dataset final (peleador y rival_*).

    Las diferencias ausentes (p. ej. tasas de un debutante) valen 0 y su ausencia se recoge en los indicadores
    d_debut, d_sin_edad, d_sin_alcance y d_sin_estadisticas. D-26.
    """
    out = pd.DataFrame(index=df.index)
    for v in VARIABLES_DIFERENCIA:
        out[f"d_{v}"] = (df[v].astype(float) - df[f"rival_{v}"].astype(float)).fillna(0.0)
    out["d_debut"] = df["hist_es_debut"].astype(float) - df["rival_hist_es_debut"].astype(float)
    out["d_sin_edad"] = df["edad"].isna().astype(float) - df["rival_edad"].isna().astype(float)
    out["d_sin_alcance"] = df["alcance_cm"].isna().astype(float) - df["rival_alcance_cm"].isna().astype(float)
    out["d_sin_estadisticas"] = (df["hist_peleas_con_estadisticas"] == 0).astype(float) - (
        df["rival_hist_peleas_con_estadisticas"] == 0
    ).astype(float)
    p = df["p_cierre_peleador"].astype(float).clip(_EPS, 1 - _EPS)
    out["logit_mercado"] = np.log(p / (1 - p))
    return out


def logit(p: float) -> float:
    """Logit con el mismo recorte que las variables."""
    p = min(max(p, _EPS), 1 - _EPS)
    return float(np.log(p / (1 - p)))
