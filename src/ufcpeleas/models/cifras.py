"""Cifras citables del informe (final/cifras.csv, T-33) y linaje cifra -> transformaciones -> fuentes (final/linaje.csv, T-34)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ufcpeleas.models import rutas
from ufcpeleas.models.bitacora import EntradaBitacora, leer_bitacora
from ufcpeleas.models.transformaciones.base import Contexto
from ufcpeleas.models.transformaciones.modelado import ESCENARIOS, FECHA_ESCENARIO, PELEA_GAETHJE, TOPURIA

CIFRAS = rutas.FINAL / "cifras.csv"
LINAJE = rutas.FINAL / "linaje.csv"

_PATRON_T = re.compile(r"\((T-\d+)\)")
_PATRON_F = re.compile(r"\((F-\d+)\)")


@dataclass
class RegistroCifras:
    """Acumula cifras con ID correlativo C-001, C-002..."""

    filas: list[dict[str, object]] = field(default_factory=list)

    def anadir(self, valor: object, descripcion: str, archivo: str, localizador: str, origen: str, transformacion: str) -> str:
        """Registra una cifra y devuelve su ID."""
        if isinstance(valor, (float, np.floating)):
            valor = round(float(valor), 6)
        id_c = f"C-{len(self.filas) + 1:03d}"
        self.filas.append(
            {
                "id_cifra": id_c,
                "valor": valor,
                "descripcion": descripcion,
                "archivo": archivo,
                "localizador": localizador,
                "origen": origen,
                "transformacion": transformacion,
            }
        )
        return id_c


def _rows_peleador(final: pd.DataFrame, url: str, antes_de: str | None = None) -> str:
    """source_row de F-01 de las peleas de un peleador (opcionalmente anteriores a una fecha)."""
    g = final[final["peleador_url"] == url]
    if antes_de:
        g = g[g["fecha"] < antes_de]
    return "F-01 source_row " + ";".join(str(x) for x in sorted(g["source_row"]))


def t33_cifras(ctx: Contexto, final: pd.DataFrame, cobertura: pd.DataFrame, tablas: dict[str, pd.DataFrame], elegido: str) -> pd.DataFrame:
    """T-33: tabla de cifras citables con valor, archivo, localizador, origen y transformación que la produce."""
    r = RegistroCifras()
    fila_g = final[(final["id_pelea"] == PELEA_GAETHJE) & (final["peleador_url"] == TOPURIA)].iloc[0]
    org_g = f"F-01 source_row {fila_g['source_row']} (fight_url {fila_g['fight_url']}); {fila_g['cuota_ids_origen']}"
    loc_g = f"id_fila = {fila_g['id_fila']}"
    ds = "final/dataset_analitico.csv"
    r.anadir(fila_g["fecha"], "Fecha oficial de Topuria vs Gaethje (event_date, D-01)", "interim/t07_peleas_f01.csv", f"id_pelea = {PELEA_GAETHJE}, columna fecha", f"F-01 source_row {fila_g['source_row']} columna event_date", "T-07")
    r.anadir(fila_g["p_cierre_peleador"], "Probabilidad de mercado (cierre, sin margen) de Topuria vs Gaethje 2026-06-14", ds, f"{loc_g}, columna p_cierre_peleador", org_g, "T-19")
    r.anadir(fila_g["cuota_n_casas"], "Casas promediadas en la cuota de cierre de Topuria vs Gaethje", ds, f"{loc_g}, columna cuota_n_casas", org_g, "T-19")
    r.anadir(fila_g["hist_victorias"], "Victorias UFC previas de Topuria antes de Gaethje (récord 9-0)", "interim/t10_historial.csv", f"{loc_g}, columna hist_victorias", _rows_peleador(final, TOPURIA, fila_g["fecha"]), "T-10")
    r.anadir(fila_g["hist_dias_desde_ultima"], "Días de inactividad de Topuria antes de Gaethje", "interim/t10_historial.csv", f"{loc_g}, columna hist_dias_desde_ultima", _rows_peleador(final, TOPURIA, fila_g["fecha"]), "T-10")

    cob = "final/cobertura_cuotas.csv"
    for ambito in ("global (F-01 1994-2026)", "desde 2021-01-01", "Ilia Topuria", "Justin Gaethje", "Paddy Pimblett"):
        c = cobertura[cobertura["ambito"] == ambito].iloc[0]
        r.anadir(c["pct_con_cuota"], f"Cobertura de cuota de cierre (%), {ambito}", cob, f"ambito = {ambito}, columna pct_con_cuota", "F-05/F-07/F-02 vía interim/t18_cuotas_consolidadas.csv (cuota_ids_origen)", "T-20")
        r.anadir(c["carga_historica_f07"], f"Peleas con cuota de la carga histórica zewnetrzne de F-07 (D-18), {ambito}", cob, f"ambito = {ambito}, columna carga_historica_f07", "F-07 source = zewnetrzne vía interim/t16_f07_cierre_por_casa.csv", "T-20")

    met = "final/modelo_metricas.csv"
    org_test = "interim/t25_predicciones_test.csv (una fila por pelea de test, 2025-01-01 a 2026-10-17; source_row de F-01 en cada fila)"
    for m in tablas["t26"].itertuples():
        for col, desc in (("log_loss", "Log-loss en test"), ("log_loss_ic95_inf", "Log-loss en test, IC95 inferior"), ("log_loss_ic95_sup", "Log-loss en test, IC95 superior"), ("brier", "Brier en test"), ("accuracy", "Accuracy en test"), ("ece", "Error de calibración esperado (ECE) en test")):
            r.anadir(getattr(m, col), f"{desc}, modelo {m.modelo}", met, f"modelo = {m.modelo}, columna {col}", org_test, "T-26")
        if m.modelo != "A_mercado":
            for col, desc in (("dif_log_loss_vs_mercado", "Diferencia de log-loss con el mercado"), ("dif_ic95_inf", "Diferencia de log-loss con el mercado, IC95 inferior"), ("dif_ic95_sup", "Diferencia de log-loss con el mercado, IC95 superior")):
                r.anadir(getattr(m, col), f"{desc}, modelo {m.modelo}", met, f"modelo = {m.modelo}, columna {col}", org_test, "T-26")
            r.anadir(m.C, f"Regularización C elegida por validación 2024, modelo {m.modelo}", met, f"modelo = {m.modelo}, columna C", "interim/t22_modelado.csv (periodos ajuste y validacion)", "T-26")
    r.anadir(int(tablas["t26"]["peleas_test"].iloc[0]), "Peleas en el conjunto de test (2025-2026)", met, "columna peleas_test", org_test, "T-26")
    r.anadir(elegido, "Modelo elegido (regla de T-26)", met, "columna elegido = True", org_test, "T-26")

    cal = "final/modelo_calibracion.csv"
    for c in tablas["t27"][tablas["t27"]["modelo"] == "A_mercado"].itertuples():
        r.anadir(c.frecuencia_victoria_favorito, f"Frecuencia de victoria del favorito de mercado en el bin {c.bin} (test)", cal, f"modelo = A_mercado, bin = {c.bin}", org_test, "T-27")

    esc = "final/escenarios.csv"
    t24 = tablas["t24"]
    for e in tablas["t29"].itertuples():
        rival = ESCENARIOS[e.escenario]
        origen = f"{_rows_peleador(final, TOPURIA)}; {_rows_peleador(final, rival)}; {e.ids_origen}"
        for col, desc in (("p_topuria", "Probabilidad de victoria de Topuria"), ("ic_inf", "Límite inferior del intervalo"), ("ic_sup", "Límite superior del intervalo")):
            r.anadir(getattr(e, col), f"{desc}, escenario {e.escenario} ({FECHA_ESCENARIO}), modelo {e.modelo}", esc, f"escenario = {e.escenario}, modelo = {e.modelo}, columna {col}", origen, "T-29")
    for e in t24.itertuples():
        rival = ESCENARIOS[e.escenario]
        r.anadir(e.edad, f"Edad de Topuria a {FECHA_ESCENARIO}", "interim/t24_escenarios_variables.csv", f"escenario = {e.escenario}, columna edad", "F-01 f_*_fighter_dob (D-25: fila más reciente de Topuria)", "T-24")
        r.anadir(e.rival_edad, f"Edad de {e.rival_nombre} a {FECHA_ESCENARIO}", "interim/t24_escenarios_variables.csv", f"escenario = {e.escenario}, columna rival_edad", "F-01 f_*_fighter_dob (D-25)", "T-24")
        r.anadir(e.rival_hist_racha, f"Racha de {e.rival_nombre} a {FECHA_ESCENARIO}", "interim/t24_escenarios_variables.csv", f"escenario = {e.escenario}, columna rival_hist_racha", _rows_peleador(final, rival), "T-24")
    r.anadir(t24["hist_racha"].iloc[0], f"Racha de Topuria a {FECHA_ESCENARIO}", "interim/t24_escenarios_variables.csv", "columna hist_racha", _rows_peleador(final, TOPURIA), "T-24")

    sen = "final/sensibilidad_d18.csv"
    for s in tablas["t30"].itertuples():
        if s.variante == "base" or s.modelo == "A_mercado" and s.escenario != "carrera_topuria":
            continue
        org = "interim/t22_modelado.csv; peleas de Topuria con carga histórica: 22fe6779c3fa649d, b1be8b41b1a4fd85, bec3154a11df3299"
        if s.escenario == "carrera_topuria":
            r.anadir(s.p_topuria, f"Probabilidad media de mercado de Topuria en su carrera ({s.variante})", sen, f"variante = {s.variante}, columna p_topuria", _rows_peleador(final, TOPURIA), "T-30")
            r.anadir(s.dif_vs_base, f"Victorias de Topuria menos las esperadas por el mercado ({s.variante})", sen, f"variante = {s.variante}, columna dif_vs_base", _rows_peleador(final, TOPURIA), "T-30")
        else:
            r.anadir(s.dif_vs_base, f"Cambio de la probabilidad de Topuria, escenario {s.escenario}, modelo {s.modelo}, variante {s.variante}", sen, f"variante = {s.variante}, escenario = {s.escenario}, modelo = {s.modelo}, columna dif_vs_base", org, "T-30")

    pre = "final/pregunta2_prepelea.csv"
    for p in tablas["t31"].itertuples():
        r.anadir(p.valor, f"Pregunta 2: {p.indicador} ({p.detalle})", pre, f"indicador = {p.indicador}", f"interim/t22_modelado.csv; {org_g}", "T-31")

    asal = "final/pregunta2_por_asalto.csv"
    t32 = tablas["t32"]
    rows_t = t32["source_rows"].iloc[0]
    for fila in t32.itertuples():
        for col in ("R1_vs_gaethje", "R2_vs_gaethje", "R3_vs_gaethje", "R4_vs_gaethje", "media_por_asalto_vs_gaethje", "media_por_asalto_previa"):
            v = getattr(fila, col)
            if pd.notna(v):
                r.anadir(v, f"Topuria por asalto: {fila.metrica}, {col}", asal, f"metrica = {fila.metrica}, columna {col}", f"F-01 source_row {rows_t}, columnas f_*_rN_*", "T-32")

    df = pd.DataFrame(r.filas)
    ctx.guardar(
        "T-33",
        df,
        CIFRAS,
        entrada=(
            "interim/t07_peleas_f01.csv (T-07); interim/t10_historial.csv (T-10); final/dataset_analitico.csv (T-19); final/cobertura_cuotas.csv (T-20); interim/t24_escenarios_variables.csv (T-24); "
            "final/modelo_metricas.csv (T-26); final/modelo_calibracion.csv (T-27); final/escenarios.csv (T-29); "
            "final/sensibilidad_d18.csv (T-30); final/pregunta2_prepelea.csv (T-31); final/pregunta2_por_asalto.csv (T-32)"
        ),
        operacion=(
            f"Registro de {len(df)} cifras citables C-001..C-{len(df):03d}: valor, descripción, archivo, localizador (fila y columna), "
            "origen (source_row de F-01, id_manual de F-02, filas de F-05/F-07 o tabla intermedia) y transformación que la produce"
        ),
        justificacion="Regla de auditoría: cada cifra del informe lleva un ID que permite recorrer el camino de vuelta hasta la fuente",
        filas_antes=sum(len(t) for t in tablas.values()),
    )
    return df


def grafo_dependencias(entradas: list[EntradaBitacora] | list[dict[str, str]]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Dependencias directas entre transformaciones y fuentes, leídas de la columna `entrada` de la bitácora."""
    deps: dict[str, set[str]] = {}
    fuentes: dict[str, set[str]] = {}
    for e in entradas:
        id_t = e["id"] if isinstance(e, dict) else e.id
        texto = e["entrada"] if isinstance(e, dict) else e.entrada
        deps[id_t] = set(_PATRON_T.findall(texto)) - {id_t}
        fuentes[id_t] = set(_PATRON_F.findall(texto))
    return deps, fuentes


def ancestros(t: str, deps: dict[str, set[str]]) -> set[str]:
    """Transformaciones de las que depende `t` (cierre transitivo, sin incluirla)."""
    vistos: set[str] = set()
    pendientes = list(deps.get(t, ()))
    while pendientes:
        x = pendientes.pop()
        if x not in vistos:
            vistos.add(x)
            pendientes.extend(deps.get(x, ()))
    return vistos


def t34_linaje(ctx: Contexto, cifras: pd.DataFrame) -> pd.DataFrame:
    """T-34: una fila por (cifra, transformación o fuente) de la que depende la cifra."""
    # Entradas de esta ejecución; si solo se ha ejecutado el modelo, las anteriores se leen de bitacora.csv.
    propias = {e.id for e in ctx.bitacora.entradas}
    previas_bitacora = [f for f in leer_bitacora() if f["id"] not in propias] if rutas.BITACORA.exists() else []
    deps, fuentes = grafo_dependencias([*previas_bitacora, *[{"id": e.id, "entrada": e.entrada} for e in ctx.bitacora.entradas]])
    filas = []
    for c in cifras.itertuples():
        directa = c.transformacion
        previas = ancestros(directa, deps)
        filas.append({"id_cifra": c.id_cifra, "nodo": directa, "tipo": "transformacion_directa"})
        for t in sorted(previas, key=lambda x: int(x[2:])):
            filas.append({"id_cifra": c.id_cifra, "nodo": t, "tipo": "transformacion_previa"})
        fs = set().union(*(fuentes.get(t, set()) for t in previas | {directa}))
        for f in sorted(fs):
            filas.append({"id_cifra": c.id_cifra, "nodo": f, "tipo": "fuente"})
    df = pd.DataFrame(filas)
    ctx.guardar(
        "T-34",
        df,
        LINAJE,
        entrada="final/cifras.csv (T-33); bitacora.csv (columna entrada de T-07..T-32)",
        operacion=(
            "Grafo de dependencias leído de la columna entrada de la bitácora (referencias (T-xx) y (F-xx)); para cada cifra, su "
            "transformación directa, el cierre transitivo de transformaciones previas y las fuentes de registro_fuentes.csv"
        ),
        justificacion="Pregunta 4 del caso: si una transformación o una fuente tiene un error, qué cifras del informe cambian",
        filas_antes=len(cifras),
    )
    return df


def cifras_afectadas(nodo: str, ruta_linaje: str | None = None, ruta_cifras: str | None = None) -> pd.DataFrame:
    """Cifras que cambian si la transformación o fuente `nodo` (p. ej. "T-07" o "F-05") tiene un error."""
    linaje = pd.read_csv(ruta_linaje or LINAJE)
    cifras = pd.read_csv(ruta_cifras or CIFRAS)
    ids = linaje.loc[linaje["nodo"] == nodo, "id_cifra"].unique()
    return cifras[cifras["id_cifra"].isin(ids)].reset_index(drop=True)


def transformaciones_registradas() -> list[str]:
    """IDs de transformación presentes en bitacora.csv."""
    return [f["id"] for f in leer_bitacora()]

