"""Transformaciones T-19 a T-21: dataset analítico final e informes de cobertura de cuotas."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.fuentes import COLUMNAS_ORIGEN
from ufcpeleas.models.transformaciones.base import Contexto
from ufcpeleas.models.transformaciones.peleas import FISICAS_PERSPECTIVA, HIST_COLUMNAS

#: Peleadores del caso, identificados por su URL de ufcstats (D-02).
PELEADORES_CLAVE: dict[str, str] = {
    "Ilia Topuria": "http://ufcstats.com/fighter-details/54f64b5e283b0ce7",
    "Justin Gaethje": "http://ufcstats.com/fighter-details/9e8f6c728eb01124",
    "Paddy Pimblett": "http://ufcstats.com/fighter-details/7826923b47f8d72a",
}

DATASET_FINAL = rutas.FINAL / "dataset_analitico.csv"

COLUMNAS_FINAL: tuple[str, ...] = (
    *COLUMNAS_ORIGEN,
    "id_fila",
    "id_pelea",
    "fight_url",
    "fecha",
    "event_name",
    "weight_class",
    "gender",
    "title_fight",
    "num_rounds",
    "posicion",
    "peleador_url",
    "peleador_nombre",
    "rival_url",
    "rival_nombre",
    "resultado_peleador",
    "objetivo_gana",
    "metodo_grupo",
    "result",
    *FISICAS_PERSPECTIVA,
    *HIST_COLUMNAS,
    *(f"rival_{c}" for c in HIST_COLUMNAS),
    "p_cierre_peleador",
    "p_cierre_rival",
    "cuota_fuente",
    "cuota_metodo",
    "cuota_n_casas",
    "cuota_casas",
    "cuota_margen_medio",
    "cuota_aproximacion",
    "cuota_carga_historica",
    "cuota_ids_origen",
    "p_verif_f05",
    "p_verif_f07",
    "p_verif_f02",
    "p_apertura_f02",
)


def t19_dataset_final(ctx: Contexto, t11: pd.DataFrame, t18: pd.DataFrame) -> pd.DataFrame:
    """T-19: dataset analítico (una fila por pelea y peleador) con historial y cuota de cierre orientada al peleador."""
    cuotas = t18[
        ["fight_url", "p_cierre_f1", "cuota_fuente", "cuota_metodo", "cuota_n_casas", "cuota_casas", "cuota_margen_medio",
         "cuota_aproximacion", "cuota_carga_historica", "cuota_ids_origen", "p_f1_f05", "p_f1_f07", "p_f1_f02", "p_apertura_f1_f02"]
    ]
    df = t11.merge(cuotas, on="fight_url", how="left", validate="many_to_one")
    es_f1 = df["posicion"] == "f_1"

    def orientar(col: str) -> pd.Series:
        return pd.Series(np.where(es_f1, df[col], 1 - df[col]), index=df.index)

    df["p_cierre_peleador"] = orientar("p_cierre_f1")
    df["p_cierre_rival"] = 1 - df["p_cierre_peleador"]
    df["p_verif_f05"] = orientar("p_f1_f05")
    df["p_verif_f07"] = orientar("p_f1_f07")
    df["p_verif_f02"] = orientar("p_f1_f02")
    df["p_apertura_f02"] = orientar("p_apertura_f1_f02")
    df["objetivo_gana"] = df["resultado_peleador"].map({"victoria": 1, "derrota": 0}).astype("Int64")
    df = df[list(COLUMNAS_FINAL)]
    ctx.guardar(
        "T-19",
        df,
        DATASET_FINAL,
        entrada="interim/t11_historial_rival.csv (T-11); interim/t18_cuotas_consolidadas.csv (T-18)",
        operacion=(
            "Unión por fight_url de T-11 con T-18; probabilidades orientadas al peleador de la fila (p_cierre_peleador = p_cierre_f1 "
            "si posicion = f_1, si no 1 - p_cierre_f1); variable objetivo objetivo_gana = 1 victoria, 0 derrota, vacío en empate y "
            "sin resultado; selección y orden de columnas (sin estadísticas de la propia pelea, que son posteriores al inicio)"
        ),
        justificacion=(
            "D-04 (empates y sin resultado fuera del objetivo pero en el historial); D-03 (solo variables previas a la pelea); "
            "D-07/D-08 (cuota de cierre sin margen); D-18 (1: cuota_carga_historica); D-23 (edad, altura y alcance)"
        ),
        filas_antes=len(t11),
    )
    return df


def t20_cobertura(ctx: Contexto, final: pd.DataFrame) -> pd.DataFrame:
    """T-20: resumen de cobertura de cuotas de cierre (global, desde 2018 y por peleador clave)."""
    peleas = final[final["posicion"] == "f_1"]
    ambitos: list[tuple[str, pd.DataFrame]] = [
        ("global (F-01 1994-2026)", peleas),
        ("desde 2018-01-14 (inicio de F-04)", peleas[peleas["fecha"] >= "2018-01-14"]),
        ("desde 2021-01-01", peleas[peleas["fecha"] >= "2021-01-01"]),
    ]
    for nombre, url in PELEADORES_CLAVE.items():
        ambitos.append((nombre, final[final["peleador_url"] == url]))
    filas = []
    for ambito, g in ambitos:
        con = g["cuota_fuente"].fillna("") != ""
        fila = {
            "ambito": ambito,
            "peleas": len(g),
            "con_cuota_cierre": int(con.sum()),
            "pct_con_cuota": round(100 * con.mean(), 2) if len(g) else np.nan,
        }
        for f in ("F-05", "F-07", "F-02"):
            fila[f"desde_{f}"] = int((g["cuota_fuente"] == f).sum())
        fila["aproximaciones"] = int(g["cuota_aproximacion"].fillna(False).astype(bool).sum())
        fila["carga_historica_f07"] = int(g["cuota_carga_historica"].fillna(False).astype(bool).sum())
        fila["fecha_min"] = g["fecha"].min()
        fila["fecha_max"] = g["fecha"].max()
        filas.append(fila)
    df = pd.DataFrame(filas)
    ctx.guardar(
        "T-20",
        df,
        rutas.FINAL / "cobertura_cuotas.csv",
        entrada="final/dataset_analitico.csv (T-19)",
        operacion=(
            "Agregación: peleas con cuota de cierre por ámbito (global y desde 2018/2021 con una fila por pelea, posicion = f_1; "
            "Topuria, Gaethje y Pimblett por peleador_url), por fuente y con carga histórica zewnetrzne de F-07"
        ),
        justificacion="D-07 (orden de fuentes); D-18 (carga histórica); D-02 (peleadores por URL); control de cobertura pedido para el informe",
        filas_antes=len(final),
    )
    return df


def t21_peleas_clave(ctx: Contexto, final: pd.DataFrame) -> pd.DataFrame:
    """T-21: listado de las peleas de Topuria, Gaethje y Pimblett con su cuota de cierre y su origen."""
    url_a_nombre = {u: n for n, u in PELEADORES_CLAVE.items()}
    g = final[final["peleador_url"].isin(url_a_nombre)].copy()
    g.insert(0, "peleador_clave", g["peleador_url"].map(url_a_nombre))
    cols = [
        "peleador_clave", "id_fila", "source_file", "source_row", "fecha", "event_name", "rival_nombre", "resultado_peleador",
        "metodo_grupo", "hist_peleas", "hist_racha", "hist_dias_desde_ultima", "p_cierre_peleador", "cuota_fuente",
        "cuota_metodo", "cuota_n_casas", "cuota_casas", "cuota_aproximacion", "cuota_carga_historica", "cuota_ids_origen", "p_verif_f05", "p_verif_f07",
        "p_verif_f02", "p_apertura_f02",
    ]
    g = g[cols].sort_values(["peleador_clave", "fecha"], kind="mergesort").reset_index(drop=True)
    ctx.guardar(
        "T-21",
        g,
        rutas.FINAL / "cuotas_peleadores_clave.csv",
        entrada="final/dataset_analitico.csv (T-19)",
        operacion="Filtro peleador_url de Topuria, Gaethje y Pimblett y selección de columnas de cuota y origen",
        justificacion="D-02 (por URL, no por nombre: excluye a Aleksandre Topuria); cobertura de cuotas de los escenarios del caso",
        filas_antes=len(final),
    )
    return g
