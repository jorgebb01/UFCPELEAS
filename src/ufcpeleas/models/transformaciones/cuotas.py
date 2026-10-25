"""Transformaciones T-12 a T-18: cuotas de cierre (F-05, F-07, F-02) unidas a las peleas de F-01."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

import numpy as np
import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.fuentes import COLUMNAS_ORIGEN, leer_fuente
from ufcpeleas.models.normalizacion import (
    americana_a_decimal,
    normalizar_nombre,
    quitar_margen,
    similitud_nombres,
)
from ufcpeleas.models.transformaciones.base import Contexto

#: D-11: mercados de predicción excluidos en F-05 y F-02.
D11_EXCLUIR_F05: frozenset[str] = frozenset({"Kalshi", "Polymarket"})
D11_EXCLUIR_F02: frozenset[str] = frozenset({"Kalshi", "Polymarket"})
#: D-11: intercambio excluido en F-07 (se conserva "Betfair Sportsbook").
D11_EXCLUIR_F07: frozenset[str] = frozenset({"Betfair"})
#: D-17: Matchbook también es un intercambio entre apostadores; se excluye con el criterio de D-11.
D17_EXCLUIR_F07: frozenset[str] = frozenset({"Matchbook"})
#: D-18 (b): filas de F-07 con source "zewnetrzne" (carga histórica, adding_date posterior a la pelea)
#: se aceptan como cierre de una casa no identificada; D-10 ya usa una de ellas para UFC 298.
F07_FUENTE_HISTORICA: str = "zewnetrzne"
#: D-14: tolerancia de fecha en la unión F-04 <-> F-01 (husos horarios de eventos en Asia/Oceanía).
TOLERANCIA_DIAS_F04: int = 2

_NIVEL = {"A": 3, "B": 2, "C": 1}


# --------------------------------------------------------------------------- T-12


def _nivel(s1: int, s2: int) -> str | None:
    """Nivel de unión a partir de la similitud de los dos nombres (A: ambos exactos, B: uno exacto, C: ambos compatibles)."""
    if min(s1, s2) < 1:
        return None
    return {4: "A", 3: "B", 2: "C"}[s1 + s2]


def t12_union_f04_f01(ctx: Contexto, t08: pd.DataFrame) -> pd.DataFrame:
    """T-12: une cada pelea de F-04 con su pelea de F-01 por fecha (+-2 días) y nombres normalizados."""
    f04 = leer_fuente("F-04")
    f01 = t08[["fight_url", "id_pelea", "fecha", "f_1_name", "f_2_name", "resultado"]].copy()
    f01["n1"] = f01["f_1_name"].map(normalizar_nombre)
    f01["n2"] = f01["f_2_name"].map(normalizar_nombre)
    f01["fecha_dt"] = pd.to_datetime(f01["fecha"])
    por_fecha: dict[pd.Timestamp, list[dict]] = defaultdict(list)
    for r in f01.to_dict("records"):
        por_fecha[r["fecha_dt"]].append(r)

    filas = []
    for r in f04.to_dict("records"):
        a1, a2 = normalizar_nombre(r["fighter_1"]), normalizar_nombre(r["fighter_2"])
        d = pd.Timestamp(r["date"])
        candidatos = []
        for k in range(-TOLERANCIA_DIAS_F04, TOLERANCIA_DIAS_F04 + 1):
            for c in por_fecha.get(d + timedelta(days=k), []):
                for orient, (s1, s2) in (
                    ("directa", (similitud_nombres(a1, c["n1"]), similitud_nombres(a2, c["n2"]))),
                    ("invertida", (similitud_nombres(a1, c["n2"]), similitud_nombres(a2, c["n1"]))),
                ):
                    nivel = _nivel(s1, s2)
                    if nivel:
                        candidatos.append(((_NIVEL[nivel], -abs(k)), nivel, orient, k, c))
        fila = {"estado_union": "no_unida", "motivo_union": "sin candidato en F-01 con fecha +-2 días y ambos nombres compatibles"}
        if candidatos:
            mejor = max(x[0] for x in candidatos)
            top = [x for x in candidatos if x[0] == mejor]
            if len({x[4]["fight_url"] for x in top}) > 1:
                fila = {"estado_union": "ambigua", "motivo_union": f"{len(top)} candidatos empatados en F-01"}
            else:
                _, nivel, orient, k, c = top[0]
                fila = {
                    "estado_union": "unida",
                    "motivo_union": "",
                    "fight_url": c["fight_url"],
                    "id_pelea": c["id_pelea"],
                    "fecha_f01": c["fecha"],
                    "dif_dias": -k,
                    "nivel_union": nivel,
                    "orientacion": orient,
                    "_resultado_f01": c["resultado"],
                }
        filas.append(fila)
    union = pd.DataFrame(filas, index=f04.index)
    df = pd.concat([f04, union], axis=1)

    # Un mismo fight_url de F-01 no puede recibir dos peleas de F-04.
    unidas = df["estado_union"] == "unida"
    repetidas = unidas & df["fight_url"].duplicated(keep=False) & df["fight_url"].notna()
    df.loc[repetidas, "estado_union"] = "ambigua"
    df.loc[repetidas, "motivo_union"] = "fight_url de F-01 reclamado por varias filas de F-04"

    # Verificación cruzada del resultado: F-04 (fighter_1/fighter_2/draw/no_contest) frente a T-08.
    def esperado(r: pd.Series) -> str:
        if r["result"] == "draw":
            return "empate"
        if r["result"] == "no_contest":
            return "sin_resultado"
        lado = 1 if r["result"] == "fighter_1" else 2
        if r["orientacion"] == "invertida":
            lado = 3 - lado
        return f"victoria_f{lado}"

    unidas = df["estado_union"] == "unida"
    df["verif_resultado"] = ""
    df.loc[unidas, "verif_resultado"] = np.where(
        df.loc[unidas].apply(esperado, axis=1) == df.loc[unidas, "_resultado_f01"], "coincide", "discrepa"
    )
    df = df.drop(columns="_resultado_f01")
    n = df["estado_union"].value_counts()
    niveles = df.loc[df["estado_union"] == "unida", "nivel_union"].value_counts()
    n_disc = int((df["verif_resultado"] == "discrepa").sum())
    no_unidas_con_cuotas = int(((df["estado_union"] != "unida") & (df["has_odds"] == True)).sum())  # noqa: E712
    for r in df[(df["estado_union"] != "unida") & (df["has_odds"] == True)].itertuples():  # noqa: E712
        ctx.avisar(f"T-12 sin unir y con cuotas en F-05: fight_id {r.fight_id} {r.date} {r.fighter_1} vs {r.fighter_2} ({r.estado_union})")
    for r in df[df["verif_resultado"] == "discrepa"].itertuples():
        ctx.avisar(f"T-12 resultado distinto F-04/F-01: fight_id {r.fight_id} {r.date} {r.fighter_1} vs {r.fighter_2}: F-04 {r.result} ({r.method}); prevalece T-08")
    ctx.avisar(
        f"T-12 unión F-04<->F-01: {n.get('unida', 0)} unidas (A={niveles.get('A', 0)}, B={niveles.get('B', 0)}, "
        f"C={niveles.get('C', 0)}), {n.get('ambigua', 0)} ambiguas, {n.get('no_unida', 0)} no unidas "
        f"({no_unidas_con_cuotas} de ellas con has_odds=True); resultado discrepante en {n_disc} unidas"
    )
    ctx.guardar(
        "T-12",
        df,
        rutas.INTERIM / "t12_union_f04_f01.csv",
        entrada="raw/archangel0x01_v3/fights.csv (F-04); interim/t08_resultados.csv (T-08)",
        operacion=(
            "Unión F-04 -> F-01 por fecha (F-01 en date +-2 días, prefiere la menor diferencia) y nombres normalizados (sin acentos, "
            "signos ni sufijos) en cualquier orden. nivel_union A = ambos nombres idénticos, B = uno idéntico y otro compatible, "
            "C = ambos compatibles. Solo se acepta un candidato único (si no: ambigua) y un fight_url de F-01 no puede recibir dos "
            f"filas. Resultado: {n.get('unida', 0)} unidas, {n.get('ambigua', 0)} ambiguas, {n.get('no_unida', 0)} no unidas; "
            f"verif_resultado compara el resultado de F-04 con T-08 ({n_disc} discrepancias)"
        ),
        justificacion=(
            "D-02 (F-04 no trae URL de ufcstats: unión por fecha + nombres solo si no hay ambigüedad, se informa el resto); "
            "D-01 (fecha F-01 = event_date). D-14 (tolerancia de +-2 días y nivel C con candidato único)"
        ),
        filas_antes=len(f04),
    )
    return df


# --------------------------------------------------------------------------- T-13


def t13_f05_moneyline(ctx: Contexto) -> pd.DataFrame:
    """T-13: filtra F-05 al mercado moneyline y excluye Kalshi y Polymarket (D-11)."""
    f05 = leer_fuente("F-05")
    ml = f05[f05["market"] == "moneyline"]
    df = ml[~ml["bookmaker"].isin(D11_EXCLUIR_F05)].copy()
    excluidas = len(ml) - len(df)
    ctx.guardar(
        "T-13",
        df,
        rutas.INTERIM / "t13_f05_moneyline.csv",
        entrada="raw/archangel0x01_v3/odds.csv (F-05)",
        operacion=(
            f"Filtro: market = moneyline ({len(ml)} de {len(f05)} filas) y bookmaker distinto de Kalshi/Polymarket "
            f"({excluidas} filas excluidas). Cada fila de F-05 es la última línea por casa antes de la pelea"
        ),
        justificacion="D-07 (cuota de cierre de ganador de la pelea, F-05 primera fuente); D-11 (excluir mercados de predicción)",
        filas_antes=len(f05),
    )
    return df


# --------------------------------------------------------------------------- T-14


def t14_f05_probabilidades(ctx: Contexto, t13: pd.DataFrame, t12: pd.DataFrame) -> pd.DataFrame:
    """T-14: convierte F-05 a probabilidad sin margen por casa y la orienta a f_1/f_2 de F-01 vía T-12."""
    df = t13.copy()
    df["dec_1"] = df["american_1"].map(americana_a_decimal)
    df["dec_2"] = df["american_2"].map(americana_a_decimal)
    dif_max = float(np.nanmax(np.abs(np.r_[df["dec_1"] - df["odds_1"], df["dec_2"] - df["odds_2"]])))
    p = [quitar_margen(1 / a, 1 / b) for a, b in zip(df["dec_1"], df["dec_2"])]
    df["p_sel_1"] = [x[0] for x in p]
    df["p_sel_2"] = [x[1] for x in p]
    df["margen"] = [x[2] for x in p]

    union = t12.loc[t12["estado_union"] == "unida", ["fight_id", "fight_url", "id_pelea", "orientacion", "fighter_1", "fighter_2"]]
    df = df.merge(union, on="fight_id", how="inner", validate="many_to_one")
    # Comprobación de que selection_1 corresponde a fighter_1 de F-04 (lo dice F-06 para moneyline).
    s11 = [similitud_nombres(normalizar_nombre(a), normalizar_nombre(b)) for a, b in zip(df["selection_1"], df["fighter_1"])]
    s12 = [similitud_nombres(normalizar_nombre(a), normalizar_nombre(b)) for a, b in zip(df["selection_1"], df["fighter_2"])]
    df["seleccion_invertida"] = [b > a for a, b in zip(s11, s12)]
    p_f04_1 = np.where(df["seleccion_invertida"], df["p_sel_2"], df["p_sel_1"])
    df["p_f1"] = np.where(df["orientacion"] == "directa", p_f04_1, 1 - p_f04_1)
    df["p_f2"] = 1 - df["p_f1"]
    df = df.rename(columns={"bookmaker": "casa"})
    n_inv = int(df["seleccion_invertida"].sum())
    ctx.guardar(
        "T-14",
        df,
        rutas.INTERIM / "t14_f05_probabilidades.csv",
        entrada="interim/t13_f05_moneyline.csv (T-13); interim/t12_union_f04_f01.csv (T-12)",
        operacion=(
            "Variables nuevas: dec_1/dec_2 desde american_1/american_2 (formato original publicado) con la fórmula de D-08 "
            f"(diferencia máxima con odds_1/odds_2 de la fuente: {dif_max:.4f}); probabilidad bruta 1/decimal y sin margen por "
            "normalización (p_sel_1, p_sel_2, margen). Unión interna con las peleas 'unida' de T-12 por fight_id y orientación a "
            f"f_1/f_2 de F-01 (p_f1, p_f2); {len(t13) - len(df)} filas sin pelea unida en F-01 se descartan; "
            f"{n_inv} filas con selection_1 = fighter_2 por nombre se reorientan"
        ),
        justificacion="D-08 (conversión y margen por normalización); D-07 (F-05 primera fuente); D-02 (solo uniones sin ambigüedad)",
        filas_antes=len(t13),
    )
    return df


# --------------------------------------------------------------------------- T-15


def t15_f07_filtro(ctx: Contexto) -> pd.DataFrame:
    """T-15: filtra F-07 a filas con fight_url, casas válidas (D-11) y anteriores a la pelea."""
    f07 = leer_fuente("F-07")
    n0 = len(f07)
    df = f07[f07["fight_url"].notna()].copy()
    n_url = len(df)
    df = df[~df["source"].isin(D11_EXCLUIR_F07)]
    n_d11 = len(df)
    df = df[~df["source"].isin(D17_EXCLUIR_F07)]
    n_prov = len(df)
    df = df[(df["odds_1"] > 1) & (df["odds_2"] > 1)]
    n_odds = len(df)
    df["adding_date_utc"] = pd.to_datetime(df["adding_date"], utc=True, format="mixed")
    df["dia_captura_utc"] = df["adding_date_utc"].dt.strftime("%Y-%m-%d")
    previa = df["dia_captura_utc"] < df["event_date"]
    historica = df["source"] == F07_FUENTE_HISTORICA
    df["tipo_instantanea"] = np.where(previa, "previa", np.where(historica, "historica_zewnetrzne", "posterior"))
    df = df[df["tipo_instantanea"] != "posterior"].copy()
    df["adding_date_utc"] = df["adding_date_utc"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    ctx.guardar(
        "T-15",
        df,
        rutas.INTERIM / "t15_f07_filtrado.csv",
        entrada="raw/jerzyszocik_v273/UFC_betting_odds.csv (F-07)",
        operacion=(
            f"Filtros sucesivos: con fight_url ({n_url}); sin source = Betfair ({n_d11}); sin Matchbook ({n_prov}); odds_1 y odds_2 > 1 "
            f"({n_odds}); instantánea previa (día UTC de adding_date < event_date) o carga histórica source = zewnetrzne ({len(df)}). "
            "tipo_instantanea = previa / historica_zewnetrzne"
        ),
        justificacion=(
            "D-07 (F-07: última instantánea por casa antes de la pelea; unión por fight_url, D-02); D-11 (excluir Betfair "
            "intercambio, conservar Betfair Sportsbook); D-17 (excluir Matchbook); D-18 (a: día UTC de adding_date anterior a "
            "event_date; b: carga histórica zewnetrzne aceptada como cierre, como D-10 en UFC 298)"
        ),
        filas_antes=n0,
    )
    return df


# --------------------------------------------------------------------------- T-16


def t16_f07_cierre_por_casa(ctx: Contexto, t15: pd.DataFrame, t08: pd.DataFrame) -> pd.DataFrame:
    """T-16: última instantánea por (pelea, casa) de F-07, probabilidad sin margen y orientación a f_1/f_2 por URL."""
    cols08 = ["fight_url", "id_pelea", "f_1_url", "f_2_url", "f_1_name", "f_2_name"]
    df = t15.merge(t08[cols08], on="fight_url", how="inner", validate="many_to_one")
    directa = (df["fighter_1_url"] == df["f_1_url"]) & (df["fighter_2_url"] == df["f_2_url"])
    invertida = (df["fighter_1_url"] == df["f_2_url"]) & (df["fighter_2_url"] == df["f_1_url"])
    sin_orientacion = int((~directa & ~invertida).sum())
    df = df[directa | invertida].copy()
    df["orientacion"] = np.where(directa[directa | invertida], "directa", "invertida")
    # Coherencia nombre-URL dentro de la pelea: en F-07 hay filas cuyo fighter_1 (nombre y odds_1) es el peleador de
    # fighter_2_url. Se comparan los nombres de F-07 con los de F-01 para las URL de la fila; solo hay dos candidatos,
    # así que no hay la ambigüedad de nombres de D-02. Las filas contradictorias o indeterminadas se descartan.
    # D-22.
    n_a = {u: normalizar_nombre(x) for u, x in zip(t08["f_1_url"], t08["f_1_name"])} | {
        u: normalizar_nombre(x) for u, x in zip(t08["f_2_url"], t08["f_2_name"])
    }
    nf1 = df["fighter_1"].map(normalizar_nombre)
    nf2 = df["fighter_2"].map(normalizar_nombre)
    u1 = df["fighter_1_url"].map(n_a)
    u2 = df["fighter_2_url"].map(n_a)
    propio = [min(similitud_nombres(a, b), similitud_nombres(c, d)) for a, b, c, d in zip(nf1, u1, nf2, u2)]
    cruzado = [min(similitud_nombres(a, d), similitud_nombres(c, b)) for a, b, c, d in zip(nf1, u1, nf2, u2)]
    df["coherencia_nombre_url"] = [
        "coherente" if p >= 1 else ("contradice" if c >= 1 else "indeterminada") for p, c in zip(propio, cruzado)
    ]
    conteo_coh = df["coherencia_nombre_url"].value_counts()
    n_contradice = int(conteo_coh.get("contradice", 0))
    n_indet = int(conteo_coh.get("indeterminada", 0))
    fechas_contra = df.loc[df["coherencia_nombre_url"] == "contradice", "event_date"]
    if n_contradice:
        ctx.avisar(
            f"T-16: {n_contradice} filas de F-07 con URL de peleador intercambiadas respecto al nombre y la cuota "
            f"(event_date {fechas_contra.min()} a {fechas_contra.max()}) y {n_indet} indeterminadas: descartadas"
        )
    df = df[df["coherencia_nombre_url"] == "coherente"].copy()
    p = [quitar_margen(1 / a, 1 / b) for a, b in zip(df["odds_1"], df["odds_2"])]
    p1 = np.array([x[0] for x in p])
    df["margen"] = [x[2] for x in p]
    df["p_f1"] = np.where(df["orientacion"] == "directa", p1, 1 - p1)
    ultima = df.groupby(["fight_url", "source"])["adding_date_utc"].transform("max")
    df = df[df["adding_date_utc"] == ultima]
    agg = (
        df.groupby(["fight_url", "id_pelea", "source"], as_index=False)
        .agg(
            p_f1=("p_f1", "mean"),
            margen=("margen", "mean"),
            filas_instantanea=("p_f1", "size"),
            adding_date_utc=("adding_date_utc", "first"),
            tipo_instantanea=("tipo_instantanea", "first"),
            source_rows=("source_row", lambda s: ";".join(str(x) for x in sorted(s))),
        )
        .rename(columns={"source": "casa"})
    )
    agg["p_f2"] = 1 - agg["p_f1"]
    agg.insert(0, "source_id", "F-07")
    agg.insert(1, "source_file", "raw/jerzyszocik_v273/UFC_betting_odds.csv")
    if sin_orientacion:
        ctx.avisar(f"T-16: {sin_orientacion} filas de F-07 con fighter_*_url que no coinciden con f_1_url/f_2_url de F-01 (descartadas)")
    ctx.guardar(
        "T-16",
        agg,
        rutas.INTERIM / "t16_f07_cierre_por_casa.csv",
        entrada="interim/t15_f07_filtrado.csv (T-15); interim/t08_resultados.csv (T-08)",
        operacion=(
            "Unión con F-01 por fight_url; orientación por fighter_1_url/fighter_2_url = f_1_url/f_2_url "
            f"({sin_orientacion} filas sin correspondencia descartadas); control de coherencia nombre-URL dentro de la pelea "
            f"({n_contradice} filas con URL intercambiadas y {n_indet} indeterminadas, descartadas); probabilidad 1/decimal sin margen por normalización; "
            "por (fight_url, casa) se queda la instantánea de adding_date máximo (media si hay varias filas con ese instante). "
            "source_rows = filas de F-07 usadas"
        ),
        justificacion=(
            "D-07 (b: F-07 = última instantánea por casa antes de la pelea); D-08 (margen); D-02 (URL de ufcstats). "
            "D-22 (descarte de filas con URL y nombre contradictorios)"
        ),
        filas_antes=len(t15),
    )
    return agg


# --------------------------------------------------------------------------- T-17

_TIPOS_F02 = ("cierre_casa", "cierre_rango", "previa_no_cierre", "apertura")


def t17_f02_manual(ctx: Contexto, t08: pd.DataFrame) -> pd.DataFrame:
    """T-17: probabilidad sin margen por pelea y tipo de cuota de manual/cuotas.csv (F-02)."""
    f02 = leer_fuente("F-02", dtype={"valor_original": str})
    n0 = len(f02)
    df = f02[(f02["mercado"] == "moneyline") & f02["fight_url"].notna()].copy()
    df["dec"] = df["valor_original"].map(americana_a_decimal)
    dif = (df["dec"] - df["valor_decimal"]).abs().max()
    if dif > 1e-4:
        raise ValueError(f"F-02: valor_decimal no coincide con D-08 (diferencia máxima {dif})")
    df = df[~df["casa_apuestas"].isin(D11_EXCLUIR_F02)]
    df["tipo"] = df["tipo_cuota"].str.replace(r"_(izquierda|derecha)$", "", regex=True)
    df["p_bruta"] = 1 / df["dec"]
    df = df.merge(t08[["fight_url", "id_pelea", "f_1_url", "f_2_url"]], on="fight_url", how="inner", validate="many_to_one")
    df["lado"] = np.select([df["fighter_url"] == df["f_1_url"], df["fighter_url"] == df["f_2_url"]], ["f_1", "f_2"], "")
    if (df["lado"] == "").any():
        raise ValueError("F-02: fighter_url que no es f_1_url ni f_2_url de la pelea")

    filas = []
    for (url, id_p, tipo), g in df.groupby(["fight_url", "id_pelea", "tipo"], sort=True):
        if tipo == "cierre_rango":
            # D-07 (c): probabilidad de cada extremo por separado y promedio; después, normalización (D-08).
            # D-19: se promedian las brutas de cada peleador antes de normalizar.
            bruta = g.groupby("lado")["p_bruta"].mean()
            if set(bruta.index) != {"f_1", "f_2"}:
                continue
            p1, _, margen = quitar_margen(bruta["f_1"], bruta["f_2"])
            n_casas, casas = 1, "BestFightOdds agregado (rango de cierre)"
        else:
            # Se emparejan los dos lados por casa. En previa_no_cierre (Covers, UFC 282) la fuente da cada lado con una
            # casa distinta ("DraftKings" / "no indicada en la fuente"): se emparejan por URL del artículo.
            # D-21.
            clave = "url" if tipo == "previa_no_cierre" else "casa_apuestas"
            ps, ms, cs = [], [], []
            for _, gc in g.groupby(clave, sort=True):
                b = gc.groupby("lado")["p_bruta"].mean()
                if set(b.index) != {"f_1", "f_2"}:
                    continue
                p1c, _, mc = quitar_margen(b["f_1"], b["f_2"])
                ps.append(p1c)
                ms.append(mc)
                cs.append("/".join(sorted(gc["casa_apuestas"].unique())))
            if not ps:
                continue
            p1, margen, n_casas, casas = float(np.mean(ps)), float(np.mean(ms)), len(ps), ";".join(cs)
        filas.append(
            {
                "source_id": "F-02",
                "source_file": "manual/cuotas.csv",
                "fight_url": url,
                "id_pelea": id_p,
                "tipo": tipo,
                "p_f1": p1,
                "p_f2": 1 - p1,
                "margen": margen,
                "n_casas": n_casas,
                "casas": casas,
                "ids_manual": ";".join(sorted(g["id_manual"])),
            }
        )
    out = pd.DataFrame(filas)
    out["tipo"] = pd.Categorical(out["tipo"], categories=_TIPOS_F02, ordered=True)
    out = out.sort_values(["fight_url", "tipo"], kind="mergesort").reset_index(drop=True)
    out["tipo"] = out["tipo"].astype(str)
    ctx.guardar(
        "T-17",
        out,
        rutas.INTERIM / "t17_f02_manual.csv",
        entrada="manual/cuotas.csv (F-02); interim/t08_resultados.csv (T-08)",
        operacion=(
            "Filtro mercado moneyline con fight_url (descarta ko_tko, sumision y moneyline_futuro); verificación de valor_decimal con "
            "D-08 desde valor_original; exclusión de Kalshi y Polymarket; orientación por fighter_url; por pelea y tipo "
            "(cierre_casa, cierre_rango, previa_no_cierre, apertura): probabilidad sin margen, media entre casas; en cierre_rango, "
            "media de las probabilidades brutas de los dos extremos de cada peleador y normalización"
        ),
        justificacion=(
            "D-07 (c: rango de cierre BFO por promedio de extremos; d: previa_no_cierre solo como aproximación; apertura solo "
            "descriptiva); D-08; D-11 (Kalshi/Polymarket); D-09 (Topuria-Gaethje: cierre por casa, no el rango de la ficha); D-10 "
            "(UFC 298 vía fight_url); D-19 (promedio de brutas antes de normalizar en el rango); D-21 (emparejamiento por URL "
            "del artículo en previa_no_cierre)"
        ),
        filas_antes=n0,
    )
    return out


# --------------------------------------------------------------------------- T-18


def t18_cuotas_consolidadas(
    ctx: Contexto, t08: pd.DataFrame, t14: pd.DataFrame, t16: pd.DataFrame, t17: pd.DataFrame
) -> pd.DataFrame:
    """T-18: una cuota de cierre por pelea de F-01 con el orden de D-07: F-05 -> F-07 -> F-02."""
    base = t08[[*COLUMNAS_ORIGEN, "id_pelea", "fight_url", "fecha", "event_name", "f_1_name", "f_1_url", "f_2_name", "f_2_url"]].copy()

    # F-05: media por casa (si una casa tiene dos filas en la misma pelea, primero se promedian, D-20) y entre casas.
    f05_casa = t14.groupby(["fight_url", "casa"], as_index=False).agg(
        p_f1=("p_f1", "mean"), margen=("margen", "mean"), rows=("source_row", lambda s: ";".join(str(x) for x in sorted(s)))
    )
    f05 = f05_casa.groupby("fight_url").agg(
        p_f1_f05=("p_f1", "mean"),
        margen_f05=("margen", "mean"),
        n_casas_f05=("casa", "size"),
        casas_f05=("casa", lambda s: ";".join(s)),
        ids_f05=("rows", lambda s: "F-05:" + ";".join(s)),
    )
    f07 = t16.groupby("fight_url").agg(
        p_f1_f07=("p_f1", "mean"),
        margen_f07=("margen", "mean"),
        n_casas_f07=("casa", "size"),
        casas_f07=("casa", lambda s: ";".join(s)),
        ids_f07=("source_rows", lambda s: "F-07:" + ";".join(s)),
        historica_f07=("tipo_instantanea", lambda s: bool((s == "historica_zewnetrzne").any())),
    )
    cierre_f02 = t17[t17["tipo"] != "apertura"].drop_duplicates("fight_url", keep="first")  # orden: casa > rango > previa
    f02 = cierre_f02.set_index("fight_url")[["p_f1", "margen", "n_casas", "casas", "ids_manual", "tipo"]].rename(
        columns={"p_f1": "p_f1_f02", "margen": "margen_f02", "n_casas": "n_casas_f02", "casas": "casas_f02", "ids_manual": "ids_f02", "tipo": "tipo_f02"}
    )
    f02["ids_f02"] = "F-02:" + f02["ids_f02"]
    apertura = t17[t17["tipo"] == "apertura"].set_index("fight_url")[["p_f1", "ids_manual"]].rename(
        columns={"p_f1": "p_apertura_f1_f02", "ids_manual": "ids_apertura_f02"}
    )
    df = base.join(f05, on="fight_url").join(f07, on="fight_url").join(f02, on="fight_url").join(apertura, on="fight_url")

    fuente, metodo, p1, n_casas, casas, ids, margen, aprox = [], [], [], [], [], [], [], []
    for r in df.itertuples(index=False):
        if pd.notna(r.p_f1_f05):
            sel = ("F-05", "media_casas_cierre", r.p_f1_f05, r.n_casas_f05, r.casas_f05, r.ids_f05, r.margen_f05, False)
        elif pd.notna(r.p_f1_f07):
            m = "media_casas_historica_f07" if r.historica_f07 else "media_casas_ultima_instantanea"
            sel = ("F-07", m, r.p_f1_f07, r.n_casas_f07, r.casas_f07, r.ids_f07, r.margen_f07, False)
        elif pd.notna(r.p_f1_f02):
            sel = ("F-02", r.tipo_f02, r.p_f1_f02, r.n_casas_f02, r.casas_f02, r.ids_f02, r.margen_f02, r.tipo_f02 == "previa_no_cierre")
        else:
            sel = ("", "", np.nan, 0, "", "", np.nan, False)
        for lista, v in zip((fuente, metodo, p1, n_casas, casas, ids, margen, aprox), sel):
            lista.append(v)
    df["cuota_fuente"] = fuente
    df["cuota_metodo"] = metodo
    df["p_cierre_f1"] = p1
    df["p_cierre_f2"] = 1 - df["p_cierre_f1"]
    df["cuota_n_casas"] = n_casas
    df["cuota_casas"] = casas
    df["cuota_ids_origen"] = ids
    df["cuota_margen_medio"] = margen
    df["cuota_aproximacion"] = aprox
    df["historica_f07"] = df["historica_f07"].astype("boolean")
    # D-18 condición (1): marca de las cuotas elegidas que incluyen la carga histórica zewnetrzne de F-07.
    df["cuota_carga_historica"] = (df["cuota_fuente"] == "F-07") & df["historica_f07"].fillna(False).astype(bool)
    cobertura = df["cuota_fuente"].value_counts()
    ctx.avisar(
        "T-18 cuotas de cierre por fuente: " + ", ".join(f"{k or 'sin cuota'}={v}" for k, v in cobertura.items())
    )
    ctx.guardar(
        "T-18",
        df,
        rutas.INTERIM / "t18_cuotas_consolidadas.csv",
        entrada=(
            "interim/t08_resultados.csv (T-08); interim/t14_f05_probabilidades.csv (T-14); interim/t16_f07_cierre_por_casa.csv (T-16); "
            "interim/t17_f02_manual.csv (T-17)"
        ),
        operacion=(
            "Unión por fight_url de las probabilidades sin margen de cada fuente (media entre casas) y selección por prioridad "
            "F-05 -> F-07 -> F-02 (en F-02: cierre_casa > cierre_rango > previa_no_cierre). p_cierre_f1/p_cierre_f2, cuota_fuente, "
            "cuota_metodo, cuota_n_casas, cuota_casas, cuota_ids_origen (filas de origen usadas), cuota_aproximacion y "
            "cuota_carga_historica (cuota de F-07 con la carga zewnetrzne); se "
            "conservan p_f1_f05, p_f1_f07, p_f1_f02 y la apertura de F-02 como verificación cruzada"
        ),
        justificacion=(
            "D-07 (orden de fuentes y cuota de cierre; apertura solo descriptiva; previa_no_cierre marcada como aproximación); "
            "D-08 (media entre casas de la probabilidad sin margen); D-18 (1: marca de la carga histórica zewnetrzne); D-10 (UFC 298 queda con F-07 por fight_url). D-20 (promedio "
            "dentro de una casa repetida en F-05)"
        ),
        filas_antes=len(t08),
    )
    return df
