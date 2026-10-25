"""Transformaciones T-22 a T-32: conjunto de modelado, evaluación temporal, escenarios, sensibilidad y pregunta 2."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.fuentes import COLUMNAS_ORIGEN, leer_fuente
from ufcpeleas.models.modelo.entrenamiento import (
    B_ESCENARIOS,
    B_METRICAS,
    SEMILLA,
    Modelo,
    accuracy,
    brier,
    ece,
    elegir_C,
    indices_bootstrap,
    log_loss,
    tabla_calibracion,
)
from ufcpeleas.models.modelo.variables import (
    INICIO_ENTRENAMIENTO,
    INICIO_TEST,
    INICIO_VALIDACION,
    columnas_combinado,
    columnas_historial,
    construir_variables,
    logit,
)
from ufcpeleas.models.normalizacion import americana_a_decimal, normalizar_nombre, quitar_margen
from ufcpeleas.models.transformaciones.base import Contexto
from ufcpeleas.models.transformaciones.cuotas import D11_EXCLUIR_F07, D17_EXCLUIR_F07
from ufcpeleas.models.transformaciones.dataset import PELEADORES_CLAVE
from ufcpeleas.models.transformaciones.peleas import _historial_peleador, valores_unicos_d25

#: Fecha supuesta de la próxima pelea (febrero de 2027). D-28.
FECHA_ESCENARIO = "2027-02-15"
#: Fecha de corte de la información de mercado (no se usan líneas capturadas después). D-28.
FECHA_CORTE = "2026-10-25"
#: Fecha de la pelea Topuria-Gaethje (D-01) y su id.
FECHA_GAETHJE = "2026-06-14"
PELEA_GAETHJE = "7208e40818401e88"

TOPURIA = PELEADORES_CLAVE["Ilia Topuria"]
ESCENARIOS: dict[str, str] = {
    "revancha_gaethje": PELEADORES_CLAVE["Justin Gaethje"],
    "pimblett": PELEADORES_CLAVE["Paddy Pimblett"],
}
#: id_manual de las líneas futuras de F-02 por escenario.
F02_FUTURAS: dict[str, tuple[str, ...]] = {
    "revancha_gaethje": tuple(f"M-{i:04d}" for i in range(109, 115)),
    "pimblett": (*(f"M-{i:04d}" for i in range(115, 121)), "M-0172", "M-0173"),
}
#: D-31: línea vigente del escenario Pimblett (prensa que cita FightOdds.io) y línea de diciembre de 2025 (solo sensibilidad).
TIPO_VIGENTE_PRENSA = "vigente_citada_prensa"
F02_PIMBLETT_DIC_2025: tuple[str, ...] = tuple(f"M-{i:04d}" for i in range(115, 121))
LIMITACION_D31 = (
    "D-31: línea Topuria -500 / Pimblett +375 publicada por Heavy (2026-10-17) citando el agregador FightOdds.io; "
    "casa de apuestas y fecha de la línea desconocidas; página del agregador no verificable"
)
#: Peleas de Topuria con cuota de la carga histórica zewnetrzne (D-18): Zalal, Jackson, Volkanovski.
PELEAS_CARGA_HISTORICA_TOPURIA: tuple[str, ...] = ("22fe6779c3fa649d", "b1be8b41b1a4fd85", "bec3154a11df3299")

MODELOS = {
    "A_mercado": "Probabilidad implícita de cierre sin margen (D-07, D-08)",
    "B_historial": "Logística sobre diferencias de historial y físicas, sin cuota",
    "C_combinado": "Logística sobre logit de la cuota + diferencias de historial y físicas",
}

_COLS_ID = [*COLUMNAS_ORIGEN, "id_fila", "id_pelea", "fight_url", "fecha", "peleador_url", "peleador_nombre", "rival_url", "rival_nombre"]


@dataclass
class EstadoModelo:
    """Resultados intermedios de T-22..T-32 que usan las cifras (T-33)."""

    C: dict[str, float] = field(default_factory=dict)
    modelo_elegido: str = ""
    datos: dict[str, pd.DataFrame] = field(default_factory=dict)


# --------------------------------------------------------------------------- T-22


def t22_conjunto_modelado(ctx: Contexto, final: pd.DataFrame) -> pd.DataFrame:
    """T-22: peleas desde 2021 con victoria/derrota y cuota, ambas perspectivas, variables del modelo y periodo temporal."""
    filtro = (final["fecha"] >= INICIO_ENTRENAMIENTO) & final["objetivo_gana"].notna() & final["p_cierre_peleador"].notna()
    df = final[filtro].copy()
    X = construir_variables(df)
    out = pd.concat(
        [df[[*_COLS_ID, "posicion", "objetivo_gana", "p_cierre_peleador", "cuota_fuente", "cuota_carga_historica"]], X],
        axis=1,
    )
    out["objetivo_gana"] = out["objetivo_gana"].astype(int)
    out["periodo"] = np.select(
        [out["fecha"] >= INICIO_TEST, out["fecha"] >= INICIO_VALIDACION], ["test", "validacion"], "ajuste"
    )
    # Fila portadora de cada pelea para evaluar (una por pelea), independiente de la posición en F-01 (f_1 siempre es el ganador).
    out["fila_evaluacion"] = out["peleador_url"] < out["rival_url"]
    out = out.sort_values(["fecha", "id_pelea", "id_fila"], kind="mergesort").reset_index(drop=True)
    if out.groupby("id_pelea").size().ne(2).any():
        raise ValueError("T-22: alguna pelea no tiene sus dos perspectivas")
    n_peleas = out["id_pelea"].nunique()
    por = out[out["fila_evaluacion"]].groupby("periodo").size()
    ctx.guardar(
        "T-22",
        out,
        rutas.INTERIM / "t22_modelado.csv",
        entrada="final/dataset_analitico.csv (T-19)",
        operacion=(
            f"Filtro fecha >= {INICIO_ENTRENAMIENTO}, objetivo_gana 0/1 y p_cierre_peleador no vacía ({n_peleas} peleas, 2 filas por "
            "pelea); variables d_* = peleador - rival (25 de historial y físicas + 4 indicadores de ausencia) con ausentes = 0, y "
            f"logit_mercado; periodo ajuste < {INICIO_VALIDACION} <= validacion < {INICIO_TEST} <= test "
            f"(peleas: ajuste {por.get('ajuste', 0)}, validacion {por.get('validacion', 0)}, test {por.get('test', 0)}); "
            "fila_evaluacion = una perspectiva por pelea (peleador_url < rival_url), sin usar posicion"
        ),
        justificacion=(
            "D-18 (2: entrenamiento desde 2021); D-04 (empates y sin resultado fuera del objetivo); D-03/D-23 (solo variables "
            "previas a la pelea); validación temporal sin barajar. ausentes = 0 con indicadores (D-26) "
            "y cortes de validación/test (D-27)"
        ),
        filas_antes=len(final),
    )
    return out


# --------------------------------------------------------------------------- T-23


def t23_cuotas_futuras(ctx: Contexto) -> pd.DataFrame:
    """T-23: líneas de mercado de los escenarios (F-02 moneyline_futuro y F-07 sin fight_url)."""
    f02 = leer_fuente("F-02", dtype={"valor_original": str})
    filas = []
    for esc, ids in F02_FUTURAS.items():
        g = f02[f02["id_manual"].isin(ids)].copy()
        g["p_bruta"] = 1 / g["valor_original"].map(americana_a_decimal)
        g["tipo"] = g["tipo_cuota"].str.replace(r"_(izquierda|derecha)$", "", regex=True)
        for tipo, gt in g.groupby("tipo", sort=True):
            bruta = gt.groupby(gt["fighter_url"] == TOPURIA)["p_bruta"].mean()
            p1, _, margen = quitar_margen(bruta[True], bruta[False])
            filas.append(
                {
                    "escenario": esc,
                    "fuente": "F-02",
                    "casa": gt["casa_apuestas"].iloc[0],
                    "tipo": tipo,
                    "p_topuria": p1,
                    "margen": margen,
                    "fecha_linea": "",
                    "ids_origen": "F-02:" + ";".join(sorted(gt["id_manual"])),
                    "anterior_a_derrota": bool(gt["id_manual"].isin(F02_PIMBLETT_DIC_2025).all()),
                    "usada": esc == "pimblett" and tipo == TIPO_VIGENTE_PRENSA,
                    "limitacion": LIMITACION_D31 if tipo == TIPO_VIGENTE_PRENSA else "",
                }
            )
    # F-07: líneas sin fight_url de la revancha, capturadas después de la primera pelea y antes del corte.
    f07 = leer_fuente("F-07")
    n1, n2 = f07["fighter_1"].map(normalizar_nombre), f07["fighter_2"].map(normalizar_nombre)
    par = {"ilia topuria", "justin gaethje"}
    es_par = pd.Series([{a, b} == par for a, b in zip(n1, n2)], index=f07.index)
    dia = pd.to_datetime(f07["adding_date"], utc=True, format="mixed").dt.strftime("%Y-%m-%d")
    g = f07[
        es_par
        & f07["fight_url"].isna()
        & (f07["event_date"] > FECHA_GAETHJE)
        & (dia > FECHA_GAETHJE)
        & (dia < FECHA_CORTE)
        & ~f07["source"].isin(D11_EXCLUIR_F07 | D17_EXCLUIR_F07)
        & (f07["odds_1"] > 1)
        & (f07["odds_2"] > 1)
    ].copy()
    g["adding_date_utc"] = pd.to_datetime(g["adding_date"], utc=True, format="mixed")
    g = g[g["adding_date_utc"] == g.groupby("source")["adding_date_utc"].transform("max")]
    hay_f07 = False
    for casa, gc in g.groupby("source", sort=True):
        ps = []
        for r in gc.itertuples():
            pa, pb, m = quitar_margen(1 / r.odds_1, 1 / r.odds_2)
            ps.append((pa if normalizar_nombre(r.fighter_1) == "ilia topuria" else pb, m))
        hay_f07 = True
        filas.append(
            {
                "escenario": "revancha_gaethje",
                "fuente": "F-07",
                "casa": casa,
                "tipo": "ultima_instantanea",
                "p_topuria": float(np.mean([x[0] for x in ps])),
                "margen": float(np.mean([x[1] for x in ps])),
                "fecha_linea": gc["adding_date_utc"].max().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ids_origen": "F-07:" + ";".join(str(x) for x in sorted(gc["source_row"])),
                "anterior_a_derrota": False,
                "usada": True,
                "limitacion": "",
            }
        )
    out = pd.DataFrame(filas)
    if not hay_f07:
        out.loc[(out["escenario"] == "revancha_gaethje") & (out["tipo"] == "cierre_rango"), "usada"] = True
    ctx.guardar(
        "T-23",
        out,
        rutas.INTERIM / "t23_cuotas_futuras.csv",
        entrada="manual/cuotas.csv (F-02); raw/jerzyszocik_v273/UFC_betting_odds.csv (F-07)",
        operacion=(
            "F-02: M-0109..M-0114 (revancha); Topuria-Pimblett: M-0172/M-0173 (vigente_citada_prensa, Heavy 2026-10-17 citando "
            "FightOdds.io, usada) y M-0115..M-0120 (diciembre de 2025, anterior a la derrota, solo sensibilidad); por tipo "
            "(apertura, cierre_rango, vigente_citada_prensa) con D-08/D-19. F-07: filas sin fight_url con los nombres normalizados Ilia Topuria y "
            f"Justin Gaethje, event_date > {FECHA_GAETHJE}, día UTC de captura entre {FECHA_GAETHJE} y {FECHA_CORTE} (exclusivos), "
            "sin Betfair/Matchbook; última instantánea por casa y probabilidad sin margen. usada = línea de referencia del escenario "
            "(F-07 antes que F-02, D-07; en Pimblett, M-0172/M-0173 por D-31)"
        ),
        justificacion=(
            "D-07 (orden F-07 -> F-02); D-08; D-11/D-17; D-19 (rango BFO). identificación por nombres de las líneas "
            "futuras sin URL (D-30) y fecha de corte (D-28); D-31 (línea vigente de Pimblett citada en prensa; la de diciembre de "
            "2025 pasa a sensibilidad)"
        ),
        filas_antes=len(f02) + len(f07),
    )
    return out


# --------------------------------------------------------------------------- T-24


def _historial_a_fecha(t09: pd.DataFrame, url: str, fecha: str) -> dict[str, object]:
    """Variables hist_* de un peleador a `fecha` con todas sus peleas anteriores (misma lógica que T-10)."""
    filas = t09[t09["peleador_url"] == url].copy()
    filas["fecha_dt"] = pd.to_datetime(filas["fecha"])
    registros = filas.assign(_idx=range(len(filas))).to_dict("records")
    if any(r["fecha_dt"] >= pd.Timestamp(fecha) for r in registros):
        raise ValueError(f"Hay peleas de {url} en o después de {fecha}")
    registros.append(
        {
            "_idx": -1,
            "fecha_dt": pd.Timestamp(fecha),
            "resultado_peleador": "escenario",
            "metodo_grupo": "otro",
            "title_fight": False,
            "duracion_seg": 0,
            "sig_strikes_att": np.nan,
            "rec_sig_strikes_att": np.nan,
            "id_pelea": "escenario",
        }
    )
    return _historial_peleador(registros)[-1]


def t24_escenarios_variables(ctx: Contexto, t08: pd.DataFrame, t09: pd.DataFrame, t23: pd.DataFrame) -> pd.DataFrame:
    """T-24: variables de cada escenario a la fecha supuesta, desde la perspectiva de Topuria."""
    unicos, _ = valores_unicos_d25(t08)
    nombres = dict(zip(t09["peleador_url"], t09["peleador_nombre"]))
    filas = []
    for esc, rival in ESCENARIOS.items():
        fila: dict[str, object] = {
            "escenario": esc,
            "fecha": FECHA_ESCENARIO,
            "peleador_url": TOPURIA,
            "peleador_nombre": nombres[TOPURIA],
            "rival_url": rival,
            "rival_nombre": nombres[rival],
        }
        for pref, url in (("", TOPURIA), ("rival_", rival)):
            for k, v in _historial_a_fecha(t09, url, FECHA_ESCENARIO).items():
                fila[f"{pref}{k}"] = v
            dob = pd.Timestamp(unicos["dob"][url])
            fila[f"{pref}edad"] = (pd.Timestamp(FECHA_ESCENARIO) - dob).days / 365.25
            fila[f"{pref}altura_cm"] = float(unicos["height_cm"][url])
            fila[f"{pref}alcance_cm"] = float(unicos["reach_cm"][url])
        ref = t23[(t23["escenario"] == esc) & t23["usada"]]
        fila["p_cierre_peleador"] = float(ref["p_topuria"].mean())
        fila["mercado_fuente"] = ";".join(sorted(ref["fuente"].unique()))
        fila["mercado_ids_origen"] = ";".join(ref["ids_origen"])
        fila["mercado_anterior_a_derrota"] = bool(ref["anterior_a_derrota"].any())
        fila["mercado_limitacion"] = "; ".join(x for x in ref["limitacion"].fillna("") if x)
        filas.append(fila)
    df = pd.DataFrame(filas)
    for c in ("hist_es_debut", "rival_hist_es_debut"):
        df[c] = df[c].astype(bool)
    X = construir_variables(df)
    out = pd.concat([df, X], axis=1)
    ctx.guardar(
        "T-24",
        out,
        rutas.INTERIM / "t24_escenarios_variables.csv",
        entrada="interim/t08_resultados.csv (T-08); interim/t09_perspectivas.csv (T-09); interim/t23_cuotas_futuras.csv (T-23)",
        operacion=(
            f"Para Topuria vs Gaethje (revancha) y Topuria vs Pimblett a {FECHA_ESCENARIO}: hist_* de ambos con todas sus peleas "
            "de F-01 (misma función que T-10; incluye la derrota de Topuria ante Gaethje y Pimblett vs Saint Denis), edad a esa "
            "fecha, altura y alcance (D-25), p_cierre_peleador = media de las líneas usadas de T-23 y variables d_*/logit_mercado"
        ),
        justificacion=(
            "D-03/D-15/D-16 (historial con peleas anteriores); D-23/D-25 (edad a la fecha, valor físico único); D-07. "
            "fecha supuesta 2027-02-15 (D-28)"
        ),
        filas_antes=len(t23),
    )
    return out


# --------------------------------------------------------------------------- T-25


def _ajustar_modelos(df: pd.DataFrame, C: dict[str, float]) -> dict[str, Modelo]:
    """Ajusta B y C sobre las filas de `df` (ambas perspectivas)."""
    return {
        "B_historial": Modelo(columnas_historial(), C["B_historial"]).ajustar(df, df["objetivo_gana"]),
        "C_combinado": Modelo(columnas_combinado(), C["C_combinado"]).ajustar(df, df["objetivo_gana"]),
    }


def t25_predicciones_test(ctx: Contexto, t22: pd.DataFrame, estado: EstadoModelo) -> pd.DataFrame:
    """T-25: elige C por validación temporal (ajuste 2021-2023, validación 2024), ajusta en 2021-2024 y predice 2025-2026."""
    aj, va = t22[t22["periodo"] == "ajuste"], t22[t22["periodo"] == "validacion"]
    tr, te = t22[t22["periodo"] != "test"], t22[t22["periodo"] == "test"]
    tablas = []
    for nombre, cols in (("B_historial", columnas_historial()), ("C_combinado", columnas_combinado())):
        C, tabla = elegir_C(cols, aj, aj["objetivo_gana"], va, va["objetivo_gana"])
        estado.C[nombre] = C
        tablas.append(f"{nombre}: C = {C} (log-loss validación {tabla['log_loss_validacion'].min():.4f})")
    modelos = _ajustar_modelos(tr, estado.C)
    out = te[[*_COLS_ID, "objetivo_gana", "p_cierre_peleador", "cuota_carga_historica", "fila_evaluacion"]].copy()
    out = out.rename(columns={"p_cierre_peleador": "p_A_mercado"})
    for nombre, m in modelos.items():
        out[f"p_{nombre}"] = m.predecir(te)
    # Control de antisimetría: p(A) + p(B) = 1 en cada pelea.
    suma = out.groupby("id_pelea")[["p_A_mercado", "p_B_historial", "p_C_combinado"]].sum()
    desvio = float((suma - 1).abs().to_numpy().max())
    if desvio > 1e-9:
        raise ValueError(f"T-25: los modelos no son antisimétricos (desvío {desvio})")
    if tr["fecha"].max() >= te["fecha"].min():
        raise ValueError("T-25: fuga temporal entre entrenamiento y test")
    out = out[out["fila_evaluacion"]].drop(columns="fila_evaluacion").reset_index(drop=True)
    estado.datos["test"] = out
    ctx.guardar(
        "T-25",
        out,
        rutas.INTERIM / "t25_predicciones_test.csv",
        entrada="interim/t22_modelado.csv (T-22)",
        operacion=(
            "Regresión logística sin intercepto sobre variables antisimétricas, escalado sin centrar. Elección de C en la rejilla "
            f"por log-loss de validación ({'; '.join(tablas)}); ajuste con {tr['id_pelea'].nunique()} peleas "
            f"({tr['fecha'].min()} a {tr['fecha'].max()}) y predicción de {out['id_pelea'].nunique()} peleas de test "
            f"({te['fecha'].min()} a {te['fecha'].max()}), una fila por pelea. Control: p(A) + p(B) = 1 (desvío máximo {desvio:.1e})"
        ),
        justificacion="D-18 (2); validación temporal sin barajar; cortes y rejilla (D-27)",
        filas_antes=len(t22),
    )
    return out


# --------------------------------------------------------------------------- T-26


def t26_metricas(ctx: Contexto, t25: pd.DataFrame, estado: EstadoModelo) -> pd.DataFrame:
    """T-26: log-loss, Brier, accuracy y ECE en test; diferencia de log-loss con el mercado e IC bootstrap pareado."""
    y = t25["objetivo_gana"].to_numpy()
    idx = indices_bootstrap(len(t25), B_METRICAS, SEMILLA)
    p_m = t25["p_A_mercado"].to_numpy()
    filas = []
    for nombre in MODELOS:
        p = t25[f"p_{nombre}"].to_numpy()
        ll = np.clip(p, 1e-6, 1 - 1e-6)
        lm = np.clip(p_m, 1e-6, 1 - 1e-6)
        perdida = -(y * np.log(ll) + (1 - y) * np.log(1 - ll))
        perdida_m = -(y * np.log(lm) + (1 - y) * np.log(1 - lm))
        dif_boot = (perdida[idx] - perdida_m[idx]).mean(axis=1)
        ll_boot = perdida[idx].mean(axis=1)
        filas.append(
            {
                "modelo": nombre,
                "descripcion": MODELOS[nombre],
                "C": estado.C.get(nombre, np.nan),
                "peleas_test": len(t25),
                "log_loss": log_loss(y, p),
                "log_loss_ic95_inf": float(np.percentile(ll_boot, 2.5)),
                "log_loss_ic95_sup": float(np.percentile(ll_boot, 97.5)),
                "brier": brier(y, p),
                "accuracy": accuracy(y, p),
                "ece": ece(y, p),
                "dif_log_loss_vs_mercado": float(perdida.mean() - perdida_m.mean()),
                "dif_ic95_inf": float(np.percentile(dif_boot, 2.5)),
                "dif_ic95_sup": float(np.percentile(dif_boot, 97.5)),
            }
        )
    df = pd.DataFrame(filas)
    # Regla de elección (D-27): menor log-loss; un modelo solo sustituye al mercado si su IC95
    # de diferencia de log-loss con el mercado queda entero por debajo de 0.
    mejores = df[(df["modelo"] != "A_mercado") & (df["dif_ic95_sup"] < 0)].sort_values("log_loss")
    estado.modelo_elegido = mejores.iloc[0]["modelo"] if len(mejores) else "A_mercado"
    df["elegido"] = df["modelo"] == estado.modelo_elegido
    ctx.guardar(
        "T-26",
        df,
        rutas.FINAL / "modelo_metricas.csv",
        entrada="interim/t25_predicciones_test.csv (T-25)",
        operacion=(
            f"Métricas en test (una fila por pelea): log-loss con IC95 bootstrap ({B_METRICAS} réplicas, semilla {SEMILLA}), Brier, "
            "accuracy (lado con p > 0,5), ECE (bins del favorito) y diferencia de log-loss con el mercado con IC95 bootstrap pareado. "
            f"Modelo elegido: {estado.modelo_elegido}"
        ),
        justificacion=(
            "Comparación pedida (mercado, historial, combinado). regla de elección = menor log-loss y solo se "
            "sustituye al mercado si el IC95 de la diferencia es < 0 (D-27); intervalos bootstrap (D-29)"
        ),
        filas_antes=len(t25),
    )
    return df


# --------------------------------------------------------------------------- T-27


def t27_calibracion(ctx: Contexto, t25: pd.DataFrame) -> pd.DataFrame:
    """T-27: tabla de calibración por modelo (probabilidad del favorito frente a frecuencia observada)."""
    y = t25["objetivo_gana"].to_numpy()
    partes = []
    for nombre in MODELOS:
        tabla = tabla_calibracion(y, t25[f"p_{nombre}"].to_numpy())
        tabla.insert(0, "modelo", nombre)
        partes.append(tabla)
    df = pd.concat(partes, ignore_index=True)
    ctx.guardar(
        "T-27",
        df,
        rutas.FINAL / "modelo_calibracion.csv",
        entrada="interim/t25_predicciones_test.csv (T-25)",
        operacion="Calibración en test: cada pelea desde el favorito de cada modelo, bins [0,5-0,6), ..., [0,9-1,0]; peleas, p media y frecuencia de victoria",
        justificacion="Métrica de calibración pedida; D-08 (probabilidades sin margen)",
        filas_antes=len(t25),
    )
    return df


# --------------------------------------------------------------------------- T-28


def t28_coeficientes(ctx: Contexto, t22: pd.DataFrame, estado: EstadoModelo) -> pd.DataFrame:
    """T-28: ajuste final de B y C con todas las peleas desde 2021 (incluido el test) y sus coeficientes."""
    modelos = _ajustar_modelos(t22, estado.C)
    estado.datos["modelos_finales"] = modelos  # type: ignore[assignment]
    partes = []
    for nombre, m in modelos.items():
        c = m.coeficientes()
        c.insert(0, "modelo", nombre)
        c["C"] = m.C
        partes.append(c)
    df = pd.concat(partes, ignore_index=True)
    ctx.guardar(
        "T-28",
        df,
        rutas.FINAL / "modelo_coeficientes.csv",
        entrada="interim/t22_modelado.csv (T-22)",
        operacion=(
            f"Ajuste final de B y C con las {t22['id_pelea'].nunique()} peleas desde {INICIO_ENTRENAMIENTO} ({t22['fecha'].max()} la "
            "última) con el C elegido en T-25; coeficientes estandarizados y en escala original"
        ),
        justificacion="D-18 (2); el modelo que predice los escenarios usa toda la información disponible antes de 2027-02-15",
        filas_antes=len(t22),
    )
    return df


# --------------------------------------------------------------------------- T-29


def _filas_por_pelea(df: pd.DataFrame) -> np.ndarray:
    """Matriz (peleas x 2) con las posiciones de las dos perspectivas de cada pelea."""
    pos = df.reset_index(drop=True).groupby("id_pelea", sort=True).indices
    return np.array([pos[k] for k in sorted(pos)])


def _bootstrap_escenarios(t22: pd.DataFrame, t24: pd.DataFrame, C: dict[str, float]) -> dict[str, np.ndarray]:
    """Probabilidades de cada escenario en B_ESCENARIOS réplicas bootstrap por peleas (semilla fija)."""
    base = t22.reset_index(drop=True)
    pares = _filas_por_pelea(base)
    idx = indices_bootstrap(len(pares), B_ESCENARIOS, SEMILLA + 1)
    res = {"B_historial": [], "C_combinado": []}
    for fila in idx:
        muestra = base.iloc[pares[fila].ravel()]
        for nombre, m in _ajustar_modelos(muestra, C).items():
            res[nombre].append(m.predecir(t24))
    return {k: np.array(v) for k, v in res.items()}


def t29_escenarios(ctx: Contexto, t22: pd.DataFrame, t23: pd.DataFrame, t24: pd.DataFrame, estado: EstadoModelo) -> pd.DataFrame:
    """T-29: probabilidad de victoria de Topuria por escenario y modelo, con intervalo."""
    modelos = estado.datos["modelos_finales"]  # type: ignore[assignment]
    boot = _bootstrap_escenarios(t22, t24, estado.C)
    filas = []
    for i, r in t24.iterrows():
        lineas = t23[(t23["escenario"] == r["escenario"]) & t23["usada"]]
        # Intervalo de mercado: líneas posteriores a la derrota (la de diciembre de 2025 de Pimblett va a T-30, D-31).
        rango = t23[(t23["escenario"] == r["escenario"]) & (t23["tipo"] != "apertura") & ~t23["anterior_a_derrota"]]
        limitacion = r["mercado_limitacion"] if isinstance(r["mercado_limitacion"], str) else ""
        filas.append(
            {
                "escenario": r["escenario"],
                "fecha_supuesta": FECHA_ESCENARIO,
                "rival_nombre": r["rival_nombre"],
                "modelo": "A_mercado",
                "p_topuria": r["p_cierre_peleador"],
                "ic_inf": float(rango["p_topuria"].min()),
                "ic_sup": float(rango["p_topuria"].max()),
                "metodo_intervalo": "mínimo y máximo de las líneas posteriores a la derrota disponibles (F-07, F-02)",
                "ids_origen": r["mercado_ids_origen"],
                "notas": "línea de diciembre de 2025, anterior a la derrota ante Gaethje" if r["mercado_anterior_a_derrota"] else "",
                "limitacion": limitacion,
            }
        )
        for nombre, m in modelos.items():
            p = float(m.predecir(t24.loc[[i]])[0])
            b = boot[nombre][:, i]
            filas.append(
                {
                    "escenario": r["escenario"],
                    "fecha_supuesta": FECHA_ESCENARIO,
                    "rival_nombre": r["rival_nombre"],
                    "modelo": nombre,
                    "p_topuria": p,
                    "ic_inf": float(np.percentile(b, 2.5)),
                    "ic_sup": float(np.percentile(b, 97.5)),
                    "metodo_intervalo": f"percentiles 2,5-97,5 de {B_ESCENARIOS} réplicas bootstrap por peleas (semilla {SEMILLA + 1})",
                    "ids_origen": "interim/t22_modelado.csv; interim/t24_escenarios_variables.csv"
                    + (f"; {r['mercado_ids_origen']}" if nombre == "C_combinado" else ""),
                    "notas": "usa la línea anterior a la derrota" if nombre == "C_combinado" and r["mercado_anterior_a_derrota"] else "",
                    "limitacion": limitacion if nombre == "C_combinado" else "",
                }
            )
    df = pd.DataFrame(filas)
    df["elegido"] = df["modelo"] == estado.modelo_elegido
    ctx.guardar(
        "T-29",
        df,
        rutas.FINAL / "escenarios.csv",
        entrada=(
            "interim/t22_modelado.csv (T-22); interim/t23_cuotas_futuras.csv (T-23); interim/t24_escenarios_variables.csv (T-24); "
            "final/modelo_coeficientes.csv (T-28); final/modelo_metricas.csv (T-26)"
        ),
        operacion=(
            "Probabilidad de victoria de Topuria por escenario: A = mercado (intervalo = mín-máx de las líneas posteriores a la "
            "derrota; en Pimblett, M-0172/M-0173 con su limitación en la columna limitacion), B y C = modelos "
            f"finales de T-28 (intervalo = bootstrap por peleas, {B_ESCENARIOS} réplicas); elegido = modelo de T-26"
        ),
        justificacion="Escenarios pedidos por el caso; D-07/D-08 (mercado); D-31 (línea vigente de Pimblett); fecha supuesta (D-28) e intervalos (D-29)",
        filas_antes=len(t24),
    )
    return df


# --------------------------------------------------------------------------- T-30


def t30_sensibilidad_d18(
    ctx: Contexto, t22: pd.DataFrame, t23: pd.DataFrame, t24: pd.DataFrame, final: pd.DataFrame, estado: EstadoModelo
) -> pd.DataFrame:
    """T-30: sensibilidad de Topuria con y sin la carga histórica (D-18, condición 3) y con la línea antigua de Pimblett (D-31)."""
    en_entrenamiento = sorted(set(PELEAS_CARGA_HISTORICA_TOPURIA) & set(t22["id_pelea"]))
    variantes = {
        "base": t22,
        "sin_3_peleas_topuria": t22[~t22["id_pelea"].isin(PELEAS_CARGA_HISTORICA_TOPURIA)],
        "sin_toda_carga_historica": t22[~t22["cuota_carga_historica"].astype(bool)],
    }
    filas = []
    for variante, datos in variantes.items():
        modelos = _ajustar_modelos(datos, estado.C)
        for i, r in t24.iterrows():
            filas.append({"variante": variante, "escenario": r["escenario"], "modelo": "A_mercado", "peleas_entrenamiento": datos["id_pelea"].nunique(), "p_topuria": r["p_cierre_peleador"]})
            for nombre, m in modelos.items():
                filas.append({"variante": variante, "escenario": r["escenario"], "modelo": nombre, "peleas_entrenamiento": datos["id_pelea"].nunique(), "p_topuria": float(m.predecir(t24.loc[[i]])[0])})
    df = pd.DataFrame(filas)
    base = df[df["variante"] == "base"].set_index(["escenario", "modelo"])["p_topuria"]
    df["dif_vs_base"] = df["p_topuria"] - df.set_index(["escenario", "modelo"]).index.map(base)
    # Historial de cuotas de Topuria: victorias esperadas por el mercado con y sin las 3 peleas.
    t = final[(final["peleador_url"] == TOPURIA) & final["objetivo_gana"].notna()]
    for variante, g in (("historial_cuotas_10_peleas", t), ("historial_cuotas_sin_3", t[~t["id_pelea"].isin(PELEAS_CARGA_HISTORICA_TOPURIA)])):
        filas_h = {
            "variante": variante,
            "escenario": "carrera_topuria",
            "modelo": "A_mercado",
            "peleas_entrenamiento": len(g),
            "p_topuria": float(g["p_cierre_peleador"].mean()),
            "dif_vs_base": float(g["objetivo_gana"].sum() - g["p_cierre_peleador"].sum()),
        }
        df = pd.concat([df, pd.DataFrame([filas_h])], ignore_index=True)
    # D-31: escenario Pimblett con la línea de diciembre de 2025 (M-0115..M-0120, anterior a la derrota) en lugar de la vigente.
    antigua = t23[(t23["escenario"] == "pimblett") & (t23["tipo"] == "cierre_rango") & t23["anterior_a_derrota"]]
    p_antigua = float(antigua["p_topuria"].iloc[0])
    fila_p = t24[t24["escenario"] == "pimblett"].copy()
    fila_p["p_cierre_peleador"] = p_antigua
    fila_p["logit_mercado"] = logit(p_antigua)
    modelos_base = _ajustar_modelos(t22, estado.C)
    base_p = df[(df["variante"] == "base") & (df["escenario"] == "pimblett")].set_index("modelo")["p_topuria"]
    for nombre, p in (("A_mercado", p_antigua), ("C_combinado", float(modelos_base["C_combinado"].predecir(fila_p)[0]))):
        df = pd.concat(
            [
                df,
                pd.DataFrame(
                    [
                        {
                            "variante": "pimblett_linea_dic_2025",
                            "escenario": "pimblett",
                            "modelo": nombre,
                            "peleas_entrenamiento": t22["id_pelea"].nunique() if nombre != "A_mercado" else 0,
                            "p_topuria": p,
                            "dif_vs_base": p - float(base_p[nombre]),
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    df["ids_origen_mercado"] = np.where(df["variante"] == "pimblett_linea_dic_2025", antigua["ids_origen"].iloc[0], "")
    ctx.avisar(f"T-30: peleas de Topuria con carga histórica dentro del entrenamiento: {en_entrenamiento or 'ninguna'}")
    ctx.guardar(
        "T-30",
        df,
        rutas.FINAL / "sensibilidad_d18.csv",
        entrada=(
            "interim/t22_modelado.csv (T-22); interim/t23_cuotas_futuras.csv (T-23); interim/t24_escenarios_variables.csv (T-24); "
            "final/dataset_analitico.csv (T-19)"
        ),
        operacion=(
            "Reajuste de B y C (C de T-25) en tres variantes: base, sin las 3 peleas de Topuria con cuota zewnetrzne (de ellas solo "
            f"{', '.join(en_entrenamiento) or 'ninguna'} está en el periodo desde 2021) y sin todas las peleas con cuota_carga_historica; "
            "dif_vs_base. Filas carrera_topuria: p media de mercado de Topuria y victorias - victorias esperadas (dif_vs_base) con 10 y con 7 peleas. "
            "Filas pimblett_linea_dic_2025: A y C del escenario Pimblett con la línea M-0115..M-0120 (-770/+510, cierre_rango) en "
            "lugar de M-0172/M-0173; dif_vs_base frente a la línea vigente"
        ),
        justificacion=(
            "D-18 (3: sensibilidad de Topuria con y sin las peleas de la carga histórica). Las variables hist_* no usan cuotas, "
            "así que Zalal y Jackson (2020) solo entrarían por el entrenamiento, que empieza en 2021. D-31 (la línea de diciembre "
            "de 2025 de Pimblett se conserva solo como sensibilidad)"
        ),
        filas_antes=len(t22),
    )
    return df


# --------------------------------------------------------------------------- T-31


def t31_pregunta2_prepelea(ctx: Contexto, t22: pd.DataFrame, final: pd.DataFrame, estado: EstadoModelo) -> pd.DataFrame:
    """T-31: probabilidad que el mercado y los modelos daban a Topuria antes de Gaethje, y contexto de sorpresa."""
    antes = t22[t22["fecha"] < FECHA_GAETHJE]
    pelea = t22[(t22["id_pelea"] == PELEA_GAETHJE) & (t22["peleador_url"] == TOPURIA)]
    modelos = _ajustar_modelos(antes, estado.C)
    filas = [
        {"indicador": "p_topuria_A_mercado", "valor": float(pelea["p_cierre_peleador"].iloc[0]), "n": int(pelea["p_cierre_peleador"].size), "detalle": "cuota de cierre sin margen, F-05 (5 casas)"},
    ]
    for nombre, m in modelos.items():
        filas.append({"indicador": f"p_topuria_{nombre}", "valor": float(m.predecir(pelea)[0]), "n": antes["id_pelea"].nunique(), "detalle": f"entrenado con peleas de {INICIO_ENTRENAMIENTO} a {antes['fecha'].max()} (antes de la pelea)"})
    # Frecuencia con que pierde un favorito de mercado con p en [0,75, 0,85) desde 2021 (una fila por pelea).
    una = t22[t22["fila_evaluacion"]]
    p = una["p_cierre_peleador"].to_numpy()
    y = una["objetivo_gana"].to_numpy()
    pf, yf = np.where(p >= 0.5, p, 1 - p), np.where(p >= 0.5, y, 1 - y)
    m = (pf >= 0.75) & (pf < 0.85)
    filas.append({"indicador": "tasa_derrota_favoritos_075_085", "valor": float(1 - yf[m].mean()), "n": int(m.sum()), "detalle": f"peleas desde {INICIO_ENTRENAMIENTO} con favorito de mercado entre 0,75 y 0,85; p media del favorito {pf[m].mean():.4f}"})
    # Topuria: victorias reales frente a esperadas por el mercado.
    t = final[(final["peleador_url"] == TOPURIA) & final["objetivo_gana"].notna()]
    filas.append({"indicador": "topuria_victorias_menos_esperadas", "valor": float(t["objetivo_gana"].sum() - t["p_cierre_peleador"].sum()), "n": len(t), "detalle": f"victorias {int(t['objetivo_gana'].sum())}, esperadas {t['p_cierre_peleador'].sum():.4f}"})
    filas.append({"indicador": "topuria_dias_inactivo_antes_gaethje", "valor": float(final.loc[(final["id_pelea"] == PELEA_GAETHJE) & (final["peleador_url"] == TOPURIA), "hist_dias_desde_ultima"].iloc[0]), "n": 1, "detalle": "hist_dias_desde_ultima (T-10)"})
    # Exploratorio: residuo medio (victoria - p de mercado) según inactividad >= 300 días, desde 2021, ambas perspectivas.
    dias = final.set_index("id_fila").loc[t22["id_fila"], "hist_dias_desde_ultima"].to_numpy()
    resid = t22["objetivo_gana"].to_numpy() - t22["p_cierre_peleador"].to_numpy()
    rng_idx = indices_bootstrap(len(resid), B_METRICAS, SEMILLA + 2)
    for etiqueta, mask in (("inactividad_300_o_mas", dias >= 300), ("inactividad_menos_300", dias < 300)):
        r = resid[mask]
        boot = np.array([resid[i][mask[i]].mean() for i in rng_idx])
        filas.append({"indicador": f"residuo_medio_{etiqueta}", "valor": float(r.mean()), "n": int(mask.sum()), "detalle": f"victoria - p mercado; IC95 bootstrap [{np.percentile(boot, 2.5):.4f}, {np.percentile(boot, 97.5):.4f}] (exploratorio)"})
    df = pd.DataFrame(filas)
    ctx.guardar(
        "T-31",
        df,
        rutas.FINAL / "pregunta2_prepelea.csv",
        entrada="interim/t22_modelado.csv (T-22); final/dataset_analitico.csv (T-19)",
        operacion=(
            f"Modelos B y C reajustados solo con peleas anteriores a {FECHA_GAETHJE} y predicción para Topuria en esa pelea; cuota de "
            "mercado; tasa de derrota de favoritos con p 0,75-0,85 desde 2021; victorias de Topuria menos las esperadas; días de "
            "inactividad; residuo medio victoria - mercado según inactividad (>= 300 días), con IC95 bootstrap"
        ),
        justificacion="Pregunta 2 del caso (¿derrota atípica o señal de cambio?); D-03 (sin fuga: solo peleas anteriores); D-18 (2)",
        filas_antes=len(t22),
    )
    return df


# --------------------------------------------------------------------------- T-32

_METRICAS_ASALTO = {
    "golpes_sig_conectados": ("sig_strikes_succ", "propio"),
    "golpes_sig_intentados": ("sig_strikes_att", "propio"),
    "golpes_sig_recibidos": ("sig_strikes_succ", "rival"),
    "golpes_sig_intentados_rival": ("sig_strikes_att", "rival"),
    "golpes_cabeza_recibidos": ("head_succ", "rival"),
    "knockdowns_dados": ("knockdowns", "propio"),
    "knockdowns_recibidos": ("knockdowns", "rival"),
    "derribos_conseguidos": ("td_1_succ", "propio"),
    "control_seg": ("ctrl", "propio"),
    "control_rival_seg": ("ctrl", "rival"),
}


def t32_pregunta2_por_asalto(ctx: Contexto, t09: pd.DataFrame) -> pd.DataFrame:
    """T-32: estadísticas por asalto de Topuria vs Gaethje (R1-R4) frente a su media por asalto en peleas anteriores."""
    f01 = leer_fuente("F-01")
    t = t09[t09["peleador_url"] == TOPURIA][["id_pelea", "fecha", "source_row", "posicion"]]
    registros = []
    for r in t.itertuples():
        fila = f01.iloc[int(r.source_row) - 1]
        yo = r.posicion[-1]
        otro = "2" if yo == "1" else "1"
        for a in range(1, 6):
            if pd.isna(fila[f"f_{yo}_r{a}_sig_strikes_att"]):
                continue
            reg = {"id_pelea": r.id_pelea, "fecha": r.fecha, "source_row": int(r.source_row), "asalto": a}
            for nombre, (col, lado) in _METRICAS_ASALTO.items():
                reg[nombre] = float(fila[f"f_{yo if lado == 'propio' else otro}_r{a}_{col}"])
            registros.append(reg)
    asaltos = pd.DataFrame(registros)
    gaethje = asaltos[asaltos["id_pelea"] == PELEA_GAETHJE].set_index("asalto")
    previos = asaltos[asaltos["fecha"] < FECHA_GAETHJE]
    filas = []
    for nombre in _METRICAS_ASALTO:
        fila = {"metrica": nombre}
        for a in gaethje.index:
            fila[f"R{a}_vs_gaethje"] = gaethje.loc[a, nombre]
        fila["media_por_asalto_vs_gaethje"] = float(gaethje[nombre].mean())
        fila["media_por_asalto_previa"] = float(previos[nombre].mean())
        fila["asaltos_previos"] = len(previos)
        fila["peleas_previas"] = previos["id_pelea"].nunique()
        filas.append(fila)
    df = pd.DataFrame(filas)
    for a in gaethje.index:
        con = gaethje.loc[a, "golpes_sig_conectados"] / gaethje.loc[a, "golpes_sig_intentados"]
        df.loc[len(df)] = {"metrica": f"precision_sig_R{a}", f"R{a}_vs_gaethje": con}
    df["source_rows"] = ";".join(str(x) for x in sorted(asaltos["source_row"].unique()))
    ctx.guardar(
        "T-32",
        df,
        rutas.FINAL / "pregunta2_por_asalto.csv",
        entrada="raw/UFC_full_data_silver_v2.csv (F-01); interim/t09_perspectivas.csv (T-09)",
        operacion=(
            "Lectura de las columnas por asalto f_*_rN_* de F-01 (descartadas en T-07) en las filas source_row de las 10 peleas de "
            "Topuria, orientadas por posicion: golpes significativos conectados/intentados/recibidos, a la cabeza recibidos, "
            f"knockdowns, derribos y control. Valores R1-R4 de la pelea con Gaethje y media por asalto en las {previos['id_pelea'].nunique()} "
            f"peleas anteriores ({len(previos)} asaltos)"
        ),
        justificacion="Pregunta 2 del caso; D-02 (por URL); D-03 (estadísticas de peleas anteriores, sin fuga, para la comparación)",
        filas_antes=len(t),
    )
    return df


def ejecutar_modelo(ctx: Contexto, final: pd.DataFrame, t08: pd.DataFrame, t09: pd.DataFrame) -> tuple[EstadoModelo, dict[str, pd.DataFrame]]:
    """Ejecuta T-22..T-32 y devuelve el estado y las tablas para las cifras."""
    estado = EstadoModelo()
    t22 = t22_conjunto_modelado(ctx, final)
    t23 = t23_cuotas_futuras(ctx)
    t24 = t24_escenarios_variables(ctx, t08, t09, t23)
    t25 = t25_predicciones_test(ctx, t22, estado)
    t26 = t26_metricas(ctx, t25, estado)
    t27 = t27_calibracion(ctx, t25)
    t28 = t28_coeficientes(ctx, t22, estado)
    t29 = t29_escenarios(ctx, t22, t23, t24, estado)
    t30 = t30_sensibilidad_d18(ctx, t22, t23, t24, final, estado)
    t31 = t31_pregunta2_prepelea(ctx, t22, final, estado)
    t32 = t32_pregunta2_por_asalto(ctx, t09)
    tablas = {"t22": t22, "t23": t23, "t24": t24, "t25": t25, "t26": t26, "t27": t27, "t28": t28, "t29": t29, "t30": t30, "t31": t31, "t32": t32}
    return estado, tablas

