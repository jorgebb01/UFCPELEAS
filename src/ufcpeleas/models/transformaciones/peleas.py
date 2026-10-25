"""Transformaciones T-07 a T-11: peleas de F-01, resultado, perspectivas e historial sin fuga temporal."""

from __future__ import annotations

import re
from collections import defaultdict
from itertools import groupby

import numpy as np
import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.fuentes import COLUMNAS_ORIGEN, leer_fuente
from ufcpeleas.models.transformaciones.base import Contexto

#: Estadísticas totales por pelea que se conservan de F-01 (sin desglose por asalto).
ESTADISTICAS: tuple[str, ...] = (
    "knockdowns",
    "total_strikes_att",
    "total_strikes_succ",
    "sig_strikes_att",
    "sig_strikes_succ",
    "takedown_att",
    "takedown_succ",
    "submission_att",
    "reversals",
    "ctrl_time_sec",
)

COLUMNAS_PELEA: tuple[str, ...] = (
    "fight_url",
    "event_url",
    "event_name",
    "event_date",
    "event_city",
    "event_state",
    "event_country",
    "referee",
    "winner",
    "num_rounds",
    "title_fight",
    "weight_class",
    "gender",
    "result",
    "result_details",
    "finish_round",
    "finish_time",
    "f_1_name",
    "f_1_url",
    "f_2_name",
    "f_2_url",
)

#: D-23: atributos de f_*_fighter_* admitidos como excepción a D-03 (no dependen de peleas posteriores).
FISICOS_D23: tuple[str, ...] = ("dob", "height_cm", "reach_cm")

#: Columnas físicas de T-09 por perspectiva (peleador y rival) y diferencias peleador - rival (D-23).
FISICAS_PERSPECTIVA: tuple[str, ...] = (
    "edad",
    "altura_cm",
    "alcance_cm",
    "rival_edad",
    "rival_altura_cm",
    "rival_alcance_cm",
    "dif_edad",
    "dif_altura_cm",
    "dif_alcance_cm",
)

#: Recuentos de D-04 (aprobada): si F-01 cambia, el pipeline se detiene en lugar de reclasificar en silencio.
D04_EMPATES = 63
D04_SIN_RESULTADO = 94
RESULTADOS_SIN_RESULTADO = ("Overturned", "Could Not Continue", "Other")

#: D-16: duración de asalto de 5 min para todas las épocas.
SEGUNDOS_ASALTO = 300


def id_pelea(fight_url: str) -> str:
    """Identificador corto de pelea: el hash final de la URL de ufcstats."""
    return fight_url.rstrip("/").rsplit("/", 1)[-1]


# --------------------------------------------------------------------------- T-07


def t07_peleas(ctx: Contexto) -> pd.DataFrame:
    """T-07: carga F-01 con IDs de origen y selecciona columnas (excluye f_*_fighter_* salvo D-23, rankings y cuotas vacías)."""
    f01 = leer_fuente("F-01")
    n_antes = len(f01)
    columnas = list(f01.columns)
    fisicos = [f"f_{i}_fighter_{a}" for i in (1, 2) for a in FISICOS_D23]
    fighter = [c for c in columnas if re.match(r"^f_[12]_fighter_", c) and c not in fisicos]
    ranking = [c for c in columnas if re.match(r"^f_[12]_ranking$", c)]
    cuotas = [c for c in columnas if re.match(r"^f_[12]_(ko_|sub_)?odds$", c)]
    por_asalto = [c for c in columnas if re.match(r"^f_[12]_r\d_", c)]
    no_vacias = [c for c in cuotas if f01[c].notna().any()]
    if no_vacias:
        raise ValueError(f"F-01: columnas de cuotas que se esperaban vacías tienen datos: {no_vacias}")
    stats = [f"f_{i}_{e}" for i in (1, 2) for e in ESTADISTICAS]
    df = f01[list(COLUMNAS_ORIGEN) + list(COLUMNAS_PELEA) + stats + fisicos].copy()
    df.insert(4, "id_pelea", df["fight_url"].map(id_pelea))
    df = df.rename(columns={"event_date": "fecha"})
    if df["fight_url"].duplicated().any():
        raise ValueError("F-01: fight_url duplicado")
    ctx.guardar(
        "T-07",
        df,
        rutas.INTERIM / "t07_peleas_f01.csv",
        entrada="raw/UFC_full_data_silver_v2.csv (F-01)",
        operacion=(
            "Carga de F-01 con source_file/source_row/source_line (registro de datos y línea física) e id_pelea "
            f"(hash de fight_url); fecha = event_date. Se conservan {len(fisicos)} columnas f_*_fighter_dob/height_cm/reach_cm y "
            f"se descartan las otras {len(fighter)} columnas f_*_fighter_*, "
            f"{len(ranking)} f_*_ranking, {len(cuotas)} columnas de cuotas (100 % vacías, verificado) y "
            f"{len(por_asalto)} columnas por asalto (siguen en raw/ por source_row). Quedan {df.shape[1]} columnas."
        ),
        justificacion=(
            "D-01 (fecha oficial = event_date de ufcstats); D-02 (peleadores por f_1_url/f_2_url); D-03 (f_*_fighter_* "
            "son snapshot actual: fuga temporal); D-23 (excepción: fecha de nacimiento, altura y alcance); D-06 (rankings snapshot); D-12 (cuotas de F-01 vacías, se toman de F-05/F-07/F-02)"
        ),
        filas_antes=n_antes,
    )
    return df


# --------------------------------------------------------------------------- T-08

_TARJETA = re.compile(r"(\d+)\s*-\s*(\d+)")


def tarjetas_dan_empate(detalle: object) -> bool | None:
    """True si las tarjetas de result_details dan empate (ningún peleador gana 2 o más tarjetas).

    Devuelve None si no hay tarjetas legibles.
    """
    if not isinstance(detalle, str):
        return None
    tarjetas = [(int(a), int(b)) for a, b in _TARJETA.findall(detalle)]
    if len(tarjetas) < 3:
        return None
    gana_1 = sum(a > b for a, b in tarjetas)
    gana_2 = sum(b > a for a, b in tarjetas)
    return gana_1 < 2 and gana_2 < 2


def grupo_metodo(result: str) -> str:
    """Agrupa `result` de F-01 en ko_tko, sumision, decision, dq u otro."""
    if result.startswith("KO/TKO") or result.startswith("TKO"):
        return "ko_tko"
    if result.startswith("Submission"):
        return "sumision"
    if result.startswith("Decision"):
        return "decision"
    if result == "DQ":
        return "dq"
    return "otro"


def duracion_segundos(finish_round: int, finish_time: str) -> int:
    """Segundos de pelea: (asalto final - 1) * 300 + reloj del asalto final (D-16)."""
    mm, ss = str(finish_time).split(":")
    return (int(finish_round) - 1) * SEGUNDOS_ASALTO + int(mm) * 60 + int(ss)


def t08_resultados(ctx: Contexto, t07: pd.DataFrame) -> pd.DataFrame:
    """T-08: clasifica cada pelea (victoria_f1, victoria_f2, empate, sin_resultado) según D-04 y F-08."""
    f08 = leer_fuente("F-08", dtype=str, keep_default_na=False)
    verif = f08.groupby("fight_url").agg(
        resultados=("resultado_normalizado", lambda s: set(s)),
        ids=("id_manual", lambda s: ";".join(sorted(s))),
    )
    df = t07.copy()
    resultado, ganador, regla, ids_manual = [], [], [], []
    for fila in df.itertuples(index=False):
        if isinstance(fila.winner, str) and fila.winner:
            if fila.winner == fila.f_1_name:
                resultado.append("victoria_f1")
                ganador.append(fila.f_1_url)
            elif fila.winner == fila.f_2_name:
                resultado.append("victoria_f2")
                ganador.append(fila.f_2_url)
            else:
                raise ValueError(f"{fila.fight_url}: winner no coincide con f_1_name ni f_2_name")
            regla.append("winner")
            ids_manual.append("")
        elif fila.result.startswith("Decision"):
            if fila.fight_url in verif.index:
                if verif.loc[fila.fight_url, "resultados"] != {"empate"}:
                    raise ValueError(f"{fila.fight_url}: F-08 no da empate unánime")
                regla.append("F-08")
                ids_manual.append(verif.loc[fila.fight_url, "ids"])
            elif tarjetas_dan_empate(fila.result_details):
                regla.append("tarjetas_empate")
                ids_manual.append("")
            else:
                raise ValueError(f"{fila.fight_url}: decisión sin ganador ni tarjetas de empate ni verificación F-08")
            resultado.append("empate")
            ganador.append("")
        elif fila.result in RESULTADOS_SIN_RESULTADO:
            resultado.append("sin_resultado")
            ganador.append("")
            regla.append("result_sin_resultado")
            ids_manual.append("")
        else:
            raise ValueError(f"{fila.fight_url}: resultado no clasificable ({fila.result})")
    df["resultado"] = resultado
    df["ganador_url"] = ganador
    df["regla_resultado"] = regla
    df["ids_manual_resultado"] = ids_manual
    df["metodo_grupo"] = df["result"].map(grupo_metodo)
    df["duracion_seg"] = [duracion_segundos(r, t) for r, t in zip(df["finish_round"], df["finish_time"])]
    n_emp = int((df["resultado"] == "empate").sum())
    n_nc = int((df["resultado"] == "sin_resultado").sum())
    n_f08 = int((df["regla_resultado"] == "F-08").sum())
    if (n_emp, n_nc) != (D04_EMPATES, D04_SIN_RESULTADO):
        raise ValueError(f"D-04 esperaba {D04_EMPATES} empates y {D04_SIN_RESULTADO} sin resultado; hay {n_emp} y {n_nc}")
    ctx.guardar(
        "T-08",
        df,
        rutas.INTERIM / "t08_resultados.csv",
        entrada="interim/t07_peleas_f01.csv (T-07); manual/resultados_verificados.csv (F-08)",
        operacion=(
            "Variable nueva resultado: winner = f_1_name/f_2_name -> victoria_f1/victoria_f2 (ganador_url = URL de ufcstats); "
            f"winner vacío con decisión -> empate ({n_emp}: {n_emp - n_f08} por tarjetas de result_details, {n_f08} por F-08 con "
            f"ids_manual_resultado); Overturned/Could Not Continue/Other -> sin_resultado ({n_nc}). Además metodo_grupo y "
            "duracion_seg = (finish_round - 1) * 300 + finish_time"
        ),
        justificacion=(
            "D-04 (empates y sin resultado; las 3 decisiones sin tarjetas se resuelven con F-08); D-02 (ganador por URL, no por "
            "nombre: el nombre solo se compara dentro de la misma pelea). duracion_seg con asaltos de 5 min: D-16"
        ),
        filas_antes=len(t07),
    )
    return df


# --------------------------------------------------------------------------- T-09

_RES_PELEADOR = {
    ("victoria_f1", 1): "victoria",
    ("victoria_f1", 2): "derrota",
    ("victoria_f2", 1): "derrota",
    ("victoria_f2", 2): "victoria",
}


def t09_perspectivas(ctx: Contexto, t08: pd.DataFrame) -> pd.DataFrame:
    """T-09: dos filas por pelea, una por peleador (perspectiva), con sus estadísticas y las del rival."""
    base = [
        *COLUMNAS_ORIGEN,
        "id_pelea",
        "fight_url",
        "fecha",
        "event_name",
        "title_fight",
        "num_rounds",
        "weight_class",
        "gender",
        "result",
        "resultado",
        "metodo_grupo",
        "duracion_seg",
    ]
    partes = []
    for yo, otro in ((1, 2), (2, 1)):
        p = t08[base].copy()
        p.insert(len(COLUMNAS_ORIGEN), "id_fila", t08["id_pelea"] + f"-f{yo}")
        p["posicion"] = f"f_{yo}"
        p["peleador_url"] = t08[f"f_{yo}_url"]
        p["peleador_nombre"] = t08[f"f_{yo}_name"]
        p["rival_url"] = t08[f"f_{otro}_url"]
        p["rival_nombre"] = t08[f"f_{otro}_name"]
        p["resultado_peleador"] = [
            _RES_PELEADOR.get((r, yo), r) for r in t08["resultado"]
        ]
        for e in ESTADISTICAS:
            p[e] = t08[f"f_{yo}_{e}"]
            p[f"rec_{e}"] = t08[f"f_{otro}_{e}"]
        # D-23: edad a la fecha de la pelea (no la actual), altura y alcance; vacío si falta el dato, sin imputar.
        fecha = pd.to_datetime(t08["fecha"])
        for pref, lado in (("", yo), ("rival_", otro)):
            nacimiento = pd.to_datetime(t08[f"f_{lado}_fighter_dob"], format="%Y-%m-%d")
            p[f"{pref}edad"] = (fecha - nacimiento).dt.days / 365.25
            p[f"{pref}altura_cm"] = t08[f"f_{lado}_fighter_height_cm"]
            p[f"{pref}alcance_cm"] = t08[f"f_{lado}_fighter_reach_cm"]
        for a in ("edad", "altura_cm", "alcance_cm"):
            p[f"dif_{a}"] = p[a] - p[f"rival_{a}"]
        partes.append(p)
    df = pd.concat(partes, ignore_index=True)
    if (df["edad"] <= 0).any():
        raise ValueError("T-09: edad no positiva a la fecha de la pelea")
    faltan = {c: int(df[c].isna().sum()) for c in ("edad", "altura_cm", "alcance_cm")}
    for attr, nombre in (("dob", "fecha de nacimiento"), ("height_cm", "altura"), ("reach_cm", "alcance")):
        largo = pd.concat(
            [t08[[f"f_{k}_url", f"f_{k}_fighter_{attr}"]].set_axis(["url", "valor"], axis=1) for k in (1, 2)]
        )
        distintos = largo.groupby("url")["valor"].nunique()
        if (distintos > 1).any():
            ctx.avisar(
                f"T-09: {int((distintos > 1).sum())} peleadores con más de un valor de {nombre} en F-01; se usa el de cada fila (propuesta D-25)"
            )
    df = df.sort_values(["fecha", "source_row", "posicion"], ascending=[True, False, True], kind="mergesort")
    df = df.reset_index(drop=True)
    ctx.guardar(
        "T-09",
        df,
        rutas.INTERIM / "t09_perspectivas.csv",
        entrada="interim/t08_resultados.csv (T-08)",
        operacion=(
            "Reestructuración: cada pelea genera 2 filas (posicion f_1 y f_2) con id_fila = id_pelea-f1/-f2, peleador_url/rival_url, "
            "resultado_peleador (victoria/derrota/empate/sin_resultado) y estadísticas propias y recibidas (rec_*) de esa pelea. "
            "Variables nuevas: edad = (fecha - f_*_fighter_dob) en días / 365,25, altura_cm, alcance_cm del peleador y del rival "
            f"(rival_*) y diferencias dif_* = peleador - rival; sin imputar (filas vacías: edad {faltan['edad']}, altura "
            f"{faltan['altura_cm']}, alcance {faltan['alcance_cm']})"
        ),
        justificacion=(
            "D-02 (perspectiva por URL de ufcstats); D-23 (edad calculada a la fecha de cada pelea; altura y alcance como "
            "atributos estáticos); D-01 (fecha = event_date)"
        ),
        filas_antes=len(t08),
    )
    return df


# --------------------------------------------------------------------------- T-10

HIST_COLUMNAS: tuple[str, ...] = (
    "hist_peleas",
    "hist_es_debut",
    "hist_victorias",
    "hist_derrotas",
    "hist_empates",
    "hist_sin_resultado",
    "hist_pct_victorias",
    "hist_racha",
    "hist_victorias_ko",
    "hist_victorias_sumision",
    "hist_victorias_decision",
    "hist_derrotas_ko",
    "hist_derrotas_sumision",
    "hist_derrotas_decision",
    "hist_peleas_titulo",
    "hist_fecha_ultima_pelea",
    "hist_id_ultima_pelea",
    "hist_dias_desde_ultima",
    "hist_peleas_365d",
    "hist_peleas_730d",
    "hist_minutos",
    "hist_peleas_con_estadisticas",
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
)


def _cociente(a: float, b: float, factor: float = 1.0) -> float:
    """a / b * factor, o NaN si b es 0."""
    return a / b * factor if b else np.nan


def _historial_peleador(filas: list[dict]) -> dict[int, dict[str, object]]:
    """Variables históricas de un peleador para cada una de sus filas, usando solo fechas anteriores.

    `filas` son registros de T-09 de un mismo peleador_url con su índice en `_idx`. Las peleas del
    mismo día (torneos de 1993-1999) no se ven entre sí: para cada fecha se usa el estado acumulado
    al cierre del día anterior con pelea. Dentro de un día, la racha se actualiza primero con las
    victorias (D-15).
    """
    acc: dict[str, float] = defaultdict(float)
    racha = 0
    fechas_previas: list[pd.Timestamp] = []
    ultima_fecha: pd.Timestamp | None = None
    ultima_id = ""
    salida: dict[int, dict[str, object]] = {}
    filas = sorted(filas, key=lambda f: f["fecha_dt"])
    for fecha, grupo in groupby(filas, key=lambda f: f["fecha_dt"]):
        dia = list(grupo)
        v, d = acc["v"], acc["d"]
        estado = {
            "hist_peleas": int(acc["n"]),
            "hist_es_debut": acc["n"] == 0,
            "hist_victorias": int(v),
            "hist_derrotas": int(d),
            "hist_empates": int(acc["e"]),
            "hist_sin_resultado": int(acc["nc"]),
            "hist_pct_victorias": _cociente(v, v + d),
            "hist_racha": racha,
            "hist_victorias_ko": int(acc["v_ko_tko"]),
            "hist_victorias_sumision": int(acc["v_sumision"]),
            "hist_victorias_decision": int(acc["v_decision"]),
            "hist_derrotas_ko": int(acc["d_ko_tko"]),
            "hist_derrotas_sumision": int(acc["d_sumision"]),
            "hist_derrotas_decision": int(acc["d_decision"]),
            "hist_peleas_titulo": int(acc["titulo"]),
            "hist_fecha_ultima_pelea": ultima_fecha.date().isoformat() if ultima_fecha is not None else "",
            "hist_id_ultima_pelea": ultima_id,
            "hist_dias_desde_ultima": (fecha - ultima_fecha).days if ultima_fecha is not None else np.nan,
            "hist_peleas_365d": sum((fecha - f).days <= 365 for f in fechas_previas),
            "hist_peleas_730d": sum((fecha - f).days <= 730 for f in fechas_previas),
            "hist_minutos": acc["seg"] / 60,
            "hist_peleas_con_estadisticas": int(acc["n_st"]),
            "hist_sig_conectados_min": _cociente(acc["sig_s"], acc["seg_st"], 60),
            "hist_sig_recibidos_min": _cociente(acc["rsig_s"], acc["seg_st"], 60),
            "hist_sig_precision": _cociente(acc["sig_s"], acc["sig_a"]),
            "hist_sig_defensa": 1 - _cociente(acc["rsig_s"], acc["rsig_a"]) if acc["rsig_a"] else np.nan,
            "hist_derribos_15min": _cociente(acc["td_s"], acc["seg_st"], 900),
            "hist_derribos_precision": _cociente(acc["td_s"], acc["td_a"]),
            "hist_derribos_defensa": 1 - _cociente(acc["rtd_s"], acc["rtd_a"]) if acc["rtd_a"] else np.nan,
            "hist_knockdowns_15min": _cociente(acc["kd"], acc["seg_st"], 900),
            "hist_knockdowns_recibidos_15min": _cociente(acc["rkd"], acc["seg_st"], 900),
            "hist_sumision_intentos_15min": _cociente(acc["sub"], acc["seg_st"], 900),
            "hist_control_pct": _cociente(acc["ctrl"], acc["seg_st"]),
        }
        for f in dia:
            salida[f["_idx"]] = estado
        # Actualización con las peleas del día (victorias primero para la racha).
        for f in sorted(dia, key=lambda f: f["resultado_peleador"] != "victoria"):
            r = f["resultado_peleador"]
            acc["n"] += 1
            if r == "victoria":
                acc["v"] += 1
                acc[f"v_{f['metodo_grupo']}"] += 1
                racha = racha + 1 if racha > 0 else 1
            elif r == "derrota":
                acc["d"] += 1
                acc[f"d_{f['metodo_grupo']}"] += 1
                racha = racha - 1 if racha < 0 else -1
            else:
                acc["e" if r == "empate" else "nc"] += 1
                racha = 0  # D-15: empate o sin resultado cortan la racha.
            acc["titulo"] += bool(f["title_fight"])
            acc["seg"] += f["duracion_seg"]
            if pd.notna(f["sig_strikes_att"]) and pd.notna(f["rec_sig_strikes_att"]):
                acc["n_st"] += 1
                acc["seg_st"] += f["duracion_seg"]
                for clave, col in _ACUMULADOS:
                    valor = f[col]
                    acc[clave] += 0 if pd.isna(valor) else valor
        fechas_previas.extend([fecha] * len(dia))
        ultima_fecha = fecha
        ultima_id = ";".join(sorted(f["id_pelea"] for f in dia))
    return salida


#: (acumulador, columna de T-09) para las tasas por minuto.
_ACUMULADOS: tuple[tuple[str, str], ...] = (
    ("sig_s", "sig_strikes_succ"),
    ("sig_a", "sig_strikes_att"),
    ("rsig_s", "rec_sig_strikes_succ"),
    ("rsig_a", "rec_sig_strikes_att"),
    ("td_s", "takedown_succ"),
    ("td_a", "takedown_att"),
    ("rtd_s", "rec_takedown_succ"),
    ("rtd_a", "rec_takedown_att"),
    ("kd", "knockdowns"),
    ("rkd", "rec_knockdowns"),
    ("sub", "submission_att"),
    ("ctrl", "ctrl_time_sec"),
)


def t10_historial(ctx: Contexto, t09: pd.DataFrame) -> pd.DataFrame:
    """T-10: variables históricas de cada peleador a la fecha de cada pelea, solo con peleas de fechas anteriores."""
    df = t09.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    por_peleador: dict[str, list[dict]] = defaultdict(list)
    for registro in df.assign(_idx=df.index).to_dict("records"):
        por_peleador[registro["peleador_url"]].append(registro)
    estados: dict[int, dict[str, object]] = {}
    for url in sorted(por_peleador):
        estados.update(_historial_peleador(por_peleador[url]))
    hist = pd.DataFrame.from_dict(estados, orient="index").reindex(df.index)[list(HIST_COLUMNAS)]
    enteros = [c for c in HIST_COLUMNAS if c.startswith(("hist_peleas", "hist_victorias", "hist_derrotas", "hist_empates", "hist_sin_", "hist_racha"))]
    hist[enteros] = hist[enteros].astype(int)
    hist["hist_es_debut"] = hist["hist_es_debut"].astype(bool)
    flotantes = [c for c in HIST_COLUMNAS if c not in enteros and c not in ("hist_es_debut", "hist_fecha_ultima_pelea", "hist_id_ultima_pelea")]
    hist[flotantes] = hist[flotantes].astype(float)
    df = pd.concat([df.drop(columns="fecha_dt"), hist], axis=1)
    fuga = df["hist_fecha_ultima_pelea"].ne("") & (df["hist_fecha_ultima_pelea"] >= df["fecha"])
    if fuga.any():
        raise ValueError(f"Fuga temporal en T-10: {int(fuga.sum())} filas con última pelea >= fecha")
    ctx.guardar(
        "T-10",
        df,
        rutas.INTERIM / "t10_historial.csv",
        entrada="interim/t09_perspectivas.csv (T-09)",
        operacion=(
            f"Variables nuevas ({len(HIST_COLUMNAS)} hist_*): récord previo (V/D/E/NC, % victorias, victorias y derrotas por método), "
            "racha, peleas de título, fecha e id de la última pelea, días desde la última, peleas en 365/730 días, minutos y "
            "promedios por minuto de golpes significativos, derribos, knockdowns, sumisiones y control; acumulados por peleador_url "
            "con peleas de fechas estrictamente anteriores. Control automático: hist_fecha_ultima_pelea < fecha en todas las filas"
        ),
        justificacion=(
            "D-03 (estadísticas de carrera recalculadas a la fecha de cada pelea, sin fuga temporal); D-04 (empates y sin resultado "
            "cuentan en el historial y en la actividad); D-15 (peleas del mismo día no se ven entre sí; empate/NC cortan la racha); "
            "D-16 (tasas por minuto con asaltos de 5 min)"
        ),
        filas_antes=len(t09),
    )
    return df


# --------------------------------------------------------------------------- T-11


def t11_historial_rival(ctx: Contexto, t10: pd.DataFrame) -> pd.DataFrame:
    """T-11: añade a cada fila el historial del rival en la misma pelea (rival_hist_*)."""
    rival = t10[["fight_url", "peleador_url", *HIST_COLUMNAS]].rename(
        columns={"peleador_url": "rival_url", **{c: f"rival_{c}" for c in HIST_COLUMNAS}}
    )
    df = t10.merge(rival, on=["fight_url", "rival_url"], how="left", validate="one_to_one")
    if len(df) != len(t10) or df["rival_hist_peleas"].isna().any():
        raise ValueError("T-11: no se encontró el historial del rival en alguna fila")
    ctx.guardar(
        "T-11",
        df,
        rutas.INTERIM / "t11_historial_rival.csv",
        entrada="interim/t10_historial.csv (T-10)",
        operacion=f"Unión de T-10 consigo misma por (fight_url, rival_url = peleador_url): {len(HIST_COLUMNAS)} columnas rival_hist_*",
        justificacion="D-02 (unión por URL); D-03 (las variables del rival también son previas a la pelea)",
        filas_antes=len(t10),
    )
    return df
