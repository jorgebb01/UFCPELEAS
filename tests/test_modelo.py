"""Tests de D-25, del modelo de probabilidad, de los escenarios, de las cifras y del linaje."""

from __future__ import annotations

import pandas as pd
import pytest

from ufcpeleas.models import rutas
from ufcpeleas.models.bitacora import leer_bitacora
from ufcpeleas.models.cifras import CIFRAS, LINAJE, cifras_afectadas, t33_cifras, t34_linaje
from ufcpeleas.models.modelo.variables import INICIO_ENTRENAMIENTO, INICIO_TEST
from ufcpeleas.models.pipeline import ejecutar
from ufcpeleas.models.transformaciones.base import Contexto
from ufcpeleas.models.transformaciones.dataset import PELEADORES_CLAVE
from ufcpeleas.models.transformaciones.modelado import FECHA_ESCENARIO, ejecutar_modelo

TOPURIA = PELEADORES_CLAVE["Ilia Topuria"]
WANG_CONG = "http://ufcstats.com/fighter-details/2997e7fe3c9d3d4a"


@pytest.fixture(scope="module")
def resultado():
    """Pipeline completo (datos + modelo + cifras + linaje)."""
    return ejecutar()


# --------------------------------------------------------------------------- D-25


def test_d25_valor_unico_por_peleador(resultado):
    final = resultado.final
    propias = final.loc[final["peleador_url"] == WANG_CONG, "alcance_cm"]
    como_rival = final.loc[final["rival_url"] == WANG_CONG, "rival_alcance_cm"]
    assert len(propias) > 1
    assert set(propias) == set(como_rival) == {165.1}  # valor de su pelea más reciente (source_row 26)
    for col in ("altura_cm", "alcance_cm"):
        assert (final.groupby("peleador_url")[col].nunique() <= 1).all(), col
    nacimiento = (pd.to_datetime(final["fecha"]) - pd.to_timedelta(final["edad"] * 365.25, unit="D")).dt.round("D")
    assert (nacimiento.groupby(final["peleador_url"]).nunique() <= 1).all()
    t09 = next(f for f in leer_bitacora() if f["id"] == "T-09")
    assert "D-25" in t09["justificacion"] and "Wang Cong" in t09["operacion"]


# --------------------------------------------------------------------------- modelo


def test_entrenamiento_sin_fuga_temporal(resultado):
    t22 = pd.read_csv(rutas.INTERIM / "t22_modelado.csv", low_memory=False)
    assert t22["fecha"].min() >= INICIO_ENTRENAMIENTO
    assert set(t22["objetivo_gana"]) == {0, 1}
    assert (t22.loc[t22["periodo"] == "test", "fecha"] >= INICIO_TEST).all()
    assert (t22.loc[t22["periodo"] != "test", "fecha"] < INICIO_TEST).all()
    assert "posicion" not in [c for c in t22.columns if c.startswith("d_")]
    t25 = pd.read_csv(rutas.INTERIM / "t25_predicciones_test.csv")
    assert (t25["fecha"] >= INICIO_TEST).all()
    assert t25["id_pelea"].is_unique  # una perspectiva por pelea
    pre = pd.read_csv(rutas.FINAL / "pregunta2_prepelea.csv").set_index("indicador")
    assert "a 2026-06-06 (antes de la pelea)" in pre.loc["p_topuria_C_combinado", "detalle"]


def test_modelos_antisimetricos(resultado):
    modelos = resultado.modelo
    t22 = modelos["t22"]
    from ufcpeleas.models.transformaciones.modelado import _ajustar_modelos

    for m in _ajustar_modelos(t22, {"B_historial": 0.01, "C_combinado": 0.03}).values():
        p = pd.Series(m.predecir(t22), index=t22.index)
        assert (p.groupby(t22["id_pelea"]).sum() - 1).abs().max() < 1e-9


def test_metricas_y_eleccion(resultado):
    met = pd.read_csv(rutas.FINAL / "modelo_metricas.csv")
    assert set(met["modelo"]) == {"A_mercado", "B_historial", "C_combinado"}
    assert met["elegido"].sum() == 1
    for col in ("log_loss", "brier", "accuracy", "ece"):
        assert met[col].notna().all()


def test_escenarios_a_fecha_supuesta(resultado):
    esc = pd.read_csv(rutas.FINAL / "escenarios.csv")
    assert set(esc["fecha_supuesta"]) == {FECHA_ESCENARIO}
    assert set(esc["escenario"]) == {"revancha_gaethje", "pimblett"}
    assert ((esc["ic_inf"] <= esc["p_topuria"] + 1e-12) & (esc["p_topuria"] <= esc["ic_sup"] + 1e-12)).all()
    v = pd.read_csv(rutas.INTERIM / "t24_escenarios_variables.csv").set_index("escenario")
    assert (v["hist_fecha_ultima_pelea"] < FECHA_ESCENARIO).all()
    assert (v["hist_fecha_ultima_pelea"] == "2026-06-14").all()  # incluye la derrota ante Gaethje
    assert (v["hist_derrotas"] == 1).all() and (v["hist_racha"] == -1).all()
    assert v.loc["pimblett", "rival_hist_fecha_ultima_pelea"] == "2026-07-11"  # Pimblett vs Saint Denis
    dob = pd.Timestamp("1997-01-21")
    assert v.loc["revancha_gaethje", "edad"] == pytest.approx((pd.Timestamp(FECHA_ESCENARIO) - dob).days / 365.25)
    assert bool(v.loc["pimblett", "mercado_anterior_a_derrota"]) is True


# --------------------------------------------------------------------------- cifras y linaje


def test_cifras_tienen_origen(resultado):
    cifras = pd.read_csv(CIFRAS)
    assert list(cifras["id_cifra"]) == [f"C-{i:03d}" for i in range(1, len(cifras) + 1)]
    for col in ("valor", "descripcion", "archivo", "localizador", "origen", "transformacion"):
        assert cifras[col].notna().all() and (cifras[col].astype(str).str.strip() != "").all(), col
    ids_t = {f["id"] for f in leer_bitacora()}
    assert set(cifras["transformacion"]) <= ids_t
    for archivo in cifras["archivo"].unique():
        assert (rutas.RAIZ / archivo).exists(), archivo
    c002 = cifras.set_index("id_cifra").loc["C-002"]
    fila = resultado.final[(resultado.final["id_fila"] == "7208e40818401e88-f2")].iloc[0]
    assert float(c002["valor"]) == pytest.approx(fila["p_cierre_peleador"], abs=1e-6)


def test_linaje_t07(resultado):
    afectadas = cifras_afectadas("T-07")
    cifras = pd.read_csv(CIFRAS)
    assert "C-001" in set(afectadas["id_cifra"])
    # T-07 es la raíz de todo lo que viene de F-01: todas las cifras dependen de ella.
    assert len(afectadas) == len(cifras)
    linaje = pd.read_csv(LINAJE)
    assert set(linaje["tipo"]) == {"transformacion_directa", "transformacion_previa", "fuente"}


def test_linaje_discrimina(resultado):
    por_asalto = set(pd.read_csv(CIFRAS).query("transformacion == 'T-32'")["id_cifra"])
    assert por_asalto
    assert por_asalto.isdisjoint(set(cifras_afectadas("F-05")["id_cifra"]))
    assert por_asalto <= set(cifras_afectadas("F-01")["id_cifra"])


def test_reproducibilidad_de_cifras(resultado):
    """Dos ejecuciones del modelo sobre los mismos datos dan exactamente las mismas cifras."""
    antes = pd.read_csv(CIFRAS)
    linaje_antes = pd.read_csv(LINAJE)
    t08 = pd.read_csv(rutas.INTERIM / "t08_resultados.csv", low_memory=False)
    t09 = pd.read_csv(rutas.INTERIM / "t09_perspectivas.csv", low_memory=False)
    ctx = Contexto()
    estado, tablas = ejecutar_modelo(ctx, resultado.final, t08, t09)
    cifras = t33_cifras(ctx, resultado.final, resultado.cobertura, tablas, estado.modelo_elegido)
    t34_linaje(ctx, cifras)
    pd.testing.assert_frame_equal(antes, pd.read_csv(CIFRAS))
    pd.testing.assert_frame_equal(linaje_antes, pd.read_csv(LINAJE))
