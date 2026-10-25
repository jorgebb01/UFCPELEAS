"""Diccionario de datos del dataset final (diccionario.csv en la raíz)."""

from __future__ import annotations

import pandas as pd

from ufcpeleas.models import rutas

F01 = "raw/UFC_full_data_silver_v2.csv (F-01)"

#: columna -> (descripción, origen, decisión aplicable)
_BASE: dict[str, tuple[str, str, str]] = {
    "source_id": ("Identificador de la fuente de la fila en registro_fuentes.csv (siempre F-01).", "T-07", "Reglas de auditoría"),
    "source_file": ("Ruta del archivo crudo de origen.", "T-07", "Reglas de auditoría"),
    "source_row": ("Número de registro de datos en el archivo crudo (1 = primer registro tras la cabecera).", "T-07", "Reglas de auditoría"),
    "source_line": ("Línea física donde empieza el registro en el archivo crudo (cabecera = línea 1; un registro puede ocupar varias líneas).", "T-07", "Reglas de auditoría"),
    "id_fila": ("Clave de la fila: id_pelea + '-f1' o '-f2' según la posición del peleador en F-01.", "T-09", "D-02"),
    "id_pelea": ("Hash final de fight_url de ufcstats; clave corta de la pelea.", f"{F01}: fight_url; T-07", "D-02"),
    "fight_url": ("URL de la pelea en ufcstats.", f"{F01}: fight_url", "D-02"),
    "fecha": ("Fecha oficial de la pelea (hora local del evento), AAAA-MM-DD.", f"{F01}: event_date; T-07", "D-01"),
    "event_name": ("Nombre del evento.", f"{F01}: event_name", ""),
    "weight_class": ("Categoría de peso.", f"{F01}: weight_class", ""),
    "gender": ("Género (M/F).", f"{F01}: gender", ""),
    "title_fight": ("True si fue pelea por el título.", f"{F01}: title_fight", ""),
    "num_rounds": ("Asaltos programados.", f"{F01}: num_rounds", ""),
    "posicion": ("Posición del peleador de la fila en F-01 (f_1 o f_2).", "T-09", "D-02"),
    "peleador_url": ("URL de ufcstats del peleador de la fila (identificador del peleador).", f"{F01}: f_1_url / f_2_url; T-09", "D-02"),
    "peleador_nombre": ("Nombre del peleador (solo descriptivo; no es clave).", f"{F01}: f_1_name / f_2_name; T-09", "D-02"),
    "rival_url": ("URL de ufcstats del rival.", f"{F01}: f_2_url / f_1_url; T-09", "D-02"),
    "rival_nombre": ("Nombre del rival (solo descriptivo).", f"{F01}: f_2_name / f_1_name; T-09", "D-02"),
    "resultado_peleador": ("Resultado para el peleador de la fila: victoria, derrota, empate o sin_resultado.", f"{F01}: winner, result, result_details; manual/resultados_verificados.csv (F-08); T-08, T-09", "D-04"),
    "objetivo_gana": ("Variable objetivo: 1 victoria, 0 derrota, vacío en empate y sin resultado.", "T-19 (desde resultado_peleador)", "D-04"),
    "metodo_grupo": ("Método agrupado: ko_tko, sumision, decision, dq u otro. Es resultado de la pelea, no predictor.", f"{F01}: result; T-08", "D-04"),
    "result": ("Método tal como lo publica F-01. Es resultado de la pelea, no predictor.", f"{F01}: result", "D-04"),
    "edad": ("Edad del peleador en años a la fecha de la pelea: (fecha - fecha de nacimiento) en días / 365,25; vacío si falta la fecha de nacimiento (sin imputar).", f"{F01}: f_1_fighter_dob / f_2_fighter_dob, event_date; T-07, T-09", "D-23, D-01"),
    "altura_cm": ("Altura del peleador en cm; vacío si falta (sin imputar).", f"{F01}: f_1_fighter_height_cm / f_2_fighter_height_cm; T-07, T-09", "D-23"),
    "alcance_cm": ("Alcance del peleador en cm; vacío si falta (sin imputar).", f"{F01}: f_1_fighter_reach_cm / f_2_fighter_reach_cm; T-07, T-09", "D-23"),
    "rival_edad": ("Edad del rival en años a la fecha de la pelea; vacío si falta.", f"{F01}: f_2_fighter_dob / f_1_fighter_dob, event_date; T-07, T-09", "D-23, D-01"),
    "rival_altura_cm": ("Altura del rival en cm; vacío si falta.", f"{F01}: f_2_fighter_height_cm / f_1_fighter_height_cm; T-07, T-09", "D-23"),
    "rival_alcance_cm": ("Alcance del rival en cm; vacío si falta.", f"{F01}: f_2_fighter_reach_cm / f_1_fighter_reach_cm; T-07, T-09", "D-23"),
    "dif_edad": ("edad - rival_edad (años); vacío si falta alguno.", "T-09", "D-23"),
    "dif_altura_cm": ("altura_cm - rival_altura_cm; vacío si falta alguno.", "T-09", "D-23"),
    "dif_alcance_cm": ("alcance_cm - rival_alcance_cm; vacío si falta alguno.", "T-09", "D-23"),
    "cuota_carga_historica": ("True si la cuota de cierre elegida procede de F-07 e incluye la carga histórica source = zewnetrzne (capturada el 2025-07-27, casa no identificada).", "raw/jerzyszocik_v273/UFC_betting_odds.csv (F-07): source, adding_date; T-15, T-16, T-18", "D-18"),
    "p_cierre_peleador": ("Probabilidad implícita de victoria del peleador, sin margen, media entre casas de la cuota de cierre.", "T-14 / T-16 / T-17 -> T-18 -> T-19", "D-07, D-08, D-09, D-10, D-11"),
    "p_cierre_rival": ("1 - p_cierre_peleador.", "T-19", "D-08"),
    "cuota_fuente": ("Fuente de la cuota de cierre usada: F-05, F-07 o F-02 (vacío si no hay cuota).", "T-18", "D-07"),
    "cuota_metodo": ("Cómo se obtuvo la cuota: media_casas_cierre (F-05), media_casas_ultima_instantanea / media_casas_historica_f07 (F-07), cierre_casa / cierre_rango / previa_no_cierre (F-02).", "T-18", "D-07, D-18, D-19, D-21"),
    "cuota_n_casas": ("Número de casas promediadas.", "T-18", "D-08"),
    "cuota_casas": ("Casas promediadas, separadas por ';'.", "T-18", "D-07, D-11"),
    "cuota_margen_medio": ("Margen medio de las casas (suma de probabilidades brutas - 1).", "T-14 / T-16 / T-17 -> T-18", "D-08"),
    "cuota_aproximacion": ("True si la cuota es una previa que no es de cierre (Covers, UFC 282).", "T-17 -> T-18", "D-07 (d)"),
    "cuota_ids_origen": ("Filas de origen de la cuota: 'F-05:' + source_row de odds.csv, 'F-07:' + source_row de UFC_betting_odds.csv o 'F-02:' + id_manual.", "T-14 / T-16 / T-17 -> T-18", "Reglas de auditoría"),
    "p_verif_f05": ("Verificación cruzada: probabilidad del peleador según F-05 (aunque no sea la fuente elegida).", "raw/archangel0x01_v3/odds.csv (F-05): american_1, american_2; T-13, T-14, T-18", "D-07, D-08, D-11"),
    "p_verif_f07": ("Verificación cruzada: probabilidad del peleador según F-07.", "raw/jerzyszocik_v273/UFC_betting_odds.csv (F-07): odds_1, odds_2; T-15, T-16, T-18", "D-07, D-08, D-11"),
    "p_verif_f02": ("Verificación cruzada: probabilidad del peleador según F-02 (cierre_casa > cierre_rango > previa).", "manual/cuotas.csv (F-02): valor_original; T-17, T-18", "D-07, D-08"),
    "p_apertura_f02": ("Probabilidad sin margen de la cuota de apertura de BFO (solo descriptiva).", "manual/cuotas.csv (F-02), tipo_cuota = apertura; T-17", "D-07 (a)"),
}

#: Variables históricas: descripción común a peleador y rival.
_HIST: dict[str, str] = {
    "hist_peleas": "Peleas UFC previas (todas, incluidas empates y sin resultado).",
    "hist_es_debut": "True si es su primera pelea en F-01 (debut UFC/era cubierta).",
    "hist_victorias": "Victorias previas.",
    "hist_derrotas": "Derrotas previas.",
    "hist_empates": "Empates previos.",
    "hist_sin_resultado": "Peleas previas sin resultado (NC).",
    "hist_pct_victorias": "Victorias / (victorias + derrotas) previas; vacío si no hay.",
    "hist_racha": "Racha al inicio de la pelea: +n victorias seguidas, -n derrotas seguidas; empate o NC la ponen a 0.",
    "hist_victorias_ko": "Victorias previas por KO/TKO.",
    "hist_victorias_sumision": "Victorias previas por sumisión.",
    "hist_victorias_decision": "Victorias previas por decisión.",
    "hist_derrotas_ko": "Derrotas previas por KO/TKO.",
    "hist_derrotas_sumision": "Derrotas previas por sumisión.",
    "hist_derrotas_decision": "Derrotas previas por decisión.",
    "hist_peleas_titulo": "Peleas de título previas.",
    "hist_fecha_ultima_pelea": "Fecha de la pelea previa más reciente (siempre < fecha).",
    "hist_id_ultima_pelea": "id_pelea de la pelea previa más reciente (varias si fue un torneo).",
    "hist_dias_desde_ultima": "Días desde la pelea previa más reciente (inactividad); vacío en el debut.",
    "hist_peleas_365d": "Peleas en los 365 días anteriores.",
    "hist_peleas_730d": "Peleas en los 730 días anteriores.",
    "hist_minutos": "Minutos de pelea previos (asaltos de 5 min).",
    "hist_peleas_con_estadisticas": "Peleas previas con estadísticas de golpeo en F-01.",
    "hist_sig_conectados_min": "Golpes significativos conectados por minuto en peleas previas.",
    "hist_sig_recibidos_min": "Golpes significativos recibidos por minuto en peleas previas.",
    "hist_sig_precision": "Golpes significativos conectados / intentados en peleas previas.",
    "hist_sig_defensa": "1 - (golpes significativos recibidos / intentados por los rivales) en peleas previas.",
    "hist_derribos_15min": "Derribos conseguidos por cada 15 minutos en peleas previas.",
    "hist_derribos_precision": "Derribos conseguidos / intentados en peleas previas.",
    "hist_derribos_defensa": "1 - (derribos recibidos / intentados por los rivales) en peleas previas.",
    "hist_knockdowns_15min": "Knockdowns conseguidos por cada 15 minutos en peleas previas.",
    "hist_knockdowns_recibidos_15min": "Knockdowns recibidos por cada 15 minutos en peleas previas.",
    "hist_sumision_intentos_15min": "Intentos de sumisión por cada 15 minutos en peleas previas.",
    "hist_control_pct": "Tiempo de control / tiempo de pelea en peleas previas.",
}

_ORIGEN_HIST = f"{F01}: winner, result, finish_round, finish_time, title_fight, f_*_knockdowns, f_*_sig_strikes_*, f_*_takedown_*, f_*_submission_att, f_*_ctrl_time_sec; T-08, T-09, T-10"


def metadatos() -> dict[str, tuple[str, str, str]]:
    """Descripción, origen y decisión de cada columna documentada del dataset final."""
    meta = dict(_BASE)
    for c, d in _HIST.items():
        meta[c] = (f"Peleador de la fila, a la fecha de la pelea y solo con peleas de fechas anteriores: {d}", _ORIGEN_HIST, "D-03, D-04, D-15, D-16")
        meta[f"rival_{c}"] = (f"Rival, a la fecha de la pelea y solo con peleas de fechas anteriores: {d}", f"{_ORIGEN_HIST}, T-11", "D-03, D-04, D-15, D-16")
    return meta


def _tipo(serie: pd.Series) -> str:
    """Tipo legible de una columna."""
    t = str(serie.dtype).lower()
    if t in ("bool", "boolean"):
        return "booleano"
    if t.startswith("int") or t.startswith("uint"):
        return "entero"
    if t.startswith("float"):
        return "decimal"
    return "texto"


def construir_diccionario(final: pd.DataFrame) -> pd.DataFrame:
    """Tabla columna/tipo/descripción/origen/decisión; falla si alguna columna no está documentada."""
    meta = metadatos()
    faltan = [c for c in final.columns if c not in meta]
    if faltan:
        raise ValueError(f"Columnas sin documentar en el diccionario: {faltan}")
    return pd.DataFrame(
        [
            {"columna": c, "tipo": _tipo(final[c]), "descripcion": meta[c][0], "origen": meta[c][1], "decision": meta[c][2]}
            for c in final.columns
        ]
    )


def escribir_diccionario(final: pd.DataFrame) -> pd.DataFrame:
    """Genera diccionario.csv en la raíz del proyecto."""
    dic = construir_diccionario(final)
    rutas.escribir_csv(dic, rutas.DICCIONARIO)
    return dic
