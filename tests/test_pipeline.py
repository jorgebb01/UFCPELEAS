"""Tests del pipeline: hashes, bitácora, fuga temporal, cuotas y trazabilidad hasta raw/."""

from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from ufcpeleas.models import rutas
from ufcpeleas.models.bitacora import Bitacora, EntradaBitacora, conservar_filas_manuales, leer_bitacora
from ufcpeleas.models.diccionario import construir_diccionario
from ufcpeleas.models.fuentes import ErrorVerificacion, contar_registros, verificar_fuentes
from ufcpeleas.models.normalizacion import americana_a_decimal, quitar_margen
from ufcpeleas.models.pipeline import ejecutar
from ufcpeleas.models.transformaciones.dataset import PELEADORES_CLAVE

SHA_F01 = "7bdfb1b9feea9bfba1c5eb210028764562673205dbae218118b91a7c73313f67"
TOPURIA = PELEADORES_CLAVE["Ilia Topuria"]
PELEA_GAETHJE = "7208e40818401e88"
PELEA_UFC298 = "bec3154a11df3299"
IDS_MANUALES = [f"T-{i:02d}" for i in range(7)]


@pytest.fixture(scope="session")
def resultado():
    """Ejecuta el pipeline completo una vez por sesión de tests."""
    return ejecutar()


@pytest.fixture(scope="session")
def final(resultado) -> pd.DataFrame:
    """Dataset analítico tal como queda escrito en disco."""
    return pd.read_csv(rutas.FINAL / "dataset_analitico.csv", keep_default_na=True, low_memory=False)


# --------------------------------------------------------------------------- hashes


def test_hashes_de_registro_coinciden_con_disco():
    verifs = verificar_fuentes()
    assert all(v.correcta for v in verifs)
    f01 = next(v for v in verifs if v.id_fuente == "F-01")
    assert f01.sha256_disco == SHA_F01
    assert f01.filas_disco == 8950  # registros CSV, no líneas físicas


def test_f01_tiene_mas_lineas_que_registros():
    ruta = rutas.RAW / "UFC_full_data_silver_v2.csv"
    with open(ruta, encoding="utf-8") as fh:
        lineas = sum(1 for _ in fh)
    assert lineas == 9221
    assert contar_registros(ruta) == 8950


def test_hash_alterado_aborta(tmp_path: Path):
    registro = pd.read_csv(rutas.REGISTRO_FUENTES, dtype=str, keep_default_na=False)
    registro.loc[registro["id_fuente"] == "F-01", "sha256"] = "0" * 64
    falso = tmp_path / "registro_fuentes.csv"
    registro.to_csv(falso, index=False)
    with pytest.raises(ErrorVerificacion, match="F-01"):
        verificar_fuentes(ruta_registro=falso)


def test_raw_sigue_intacto_tras_el_pipeline(resultado):
    assert all(v.correcta for v in verificar_fuentes())


def test_no_se_puede_escribir_en_raw_ni_manual():
    df = pd.DataFrame({"a": [1]})
    for ruta in (rutas.RAW / "x.csv", rutas.MANUAL / "x.csv"):
        with pytest.raises(PermissionError):
            rutas.escribir_csv(df, ruta)


# --------------------------------------------------------------------------- bitácora


def test_bitacora_recuento_de_filas(resultado):
    filas = leer_bitacora()
    ids = [f["id"] for f in filas]
    n_pipeline = len(resultado.contexto.bitacora.entradas)
    assert n_pipeline == 15
    assert len(filas) == len(IDS_MANUALES) + n_pipeline
    assert ids[: len(IDS_MANUALES)] == IDS_MANUALES
    assert ids[len(IDS_MANUALES):] == [f"T-{i:02d}" for i in range(7, 7 + n_pipeline)]
    assert len(set(ids)) == len(ids)


def test_bitacora_filas_despues_coinciden_con_salidas(resultado):
    for fila in leer_bitacora():
        if fila["id"] in IDS_MANUALES:
            continue
        assert fila["responsable"] and fila["fecha"] and fila["justificacion"]
        assert "D-" in fila["justificacion"], fila["id"]
        assert int(fila["filas_despues"]) == contar_registros(rutas.RAIZ / fila["salida"]), fila["id"]


def test_bitacora_conserva_filas_manuales_literalmente(resultado):
    try:
        original = subprocess.run(
            ["git", "show", "fc478cf:bitacora.csv"], cwd=rutas.RAIZ, capture_output=True, check=True
        ).stdout.decode("utf-8")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git no disponible")
    actual = rutas.BITACORA.read_bytes().decode("utf-8")
    assert actual.startswith(conservar_filas_manuales(original))
    assert conservar_filas_manuales(actual) == original


def test_bitacora_idempotente(tmp_path: Path, monkeypatch):
    copia = tmp_path / "bitacora.csv"
    shutil.copy(rutas.BITACORA, copia)
    monkeypatch.setattr(rutas, "_ARCHIVOS_RAIZ_PERMITIDOS", (copia,))
    for _ in range(2):
        b = Bitacora(ruta=copia)
        b.registrar(EntradaBitacora("T-07", "e", "o", "D-01", 1, 1, "interim/x.csv"))
        b.escribir()
    filas = leer_bitacora(copia)
    assert [f["id"] for f in filas] == [*IDS_MANUALES, "T-07"]


def test_bitacora_rechaza_ids_manuales():
    with pytest.raises(ValueError):
        Bitacora().registrar(EntradaBitacora("T-03", "e", "o", "j", 0, 0, "s"))


# --------------------------------------------------------------------------- D-04, D-08


def test_d04_clasificacion_de_resultados(resultado):
    t08 = pd.read_csv(rutas.INTERIM / "t08_resultados.csv", low_memory=False)
    conteo = t08["resultado"].value_counts()
    assert conteo["empate"] == 63
    assert conteo["sin_resultado"] == 94
    f08 = t08[t08["regla_resultado"] == "F-08"]
    assert set(f08["id_pelea"]) == {"c078544a32e18ba3", "96c247ba0eb1ac65", "a1c1e3c1e9c6cf1e"}


def test_d08_conversion_y_margen():
    assert americana_a_decimal("+1,200") == 13.0
    assert americana_a_decimal("-250") == 1.4
    assert americana_a_decimal(-235) == 1.4255
    p1, p2, margen = quitar_margen(0.6, 0.5)
    assert p1 + p2 == pytest.approx(1)
    assert margen == pytest.approx(0.1)


# --------------------------------------------------------------------------- fuga temporal


def test_sin_fuga_temporal_global(final):
    con_previa = final["hist_fecha_ultima_pelea"].notna()
    assert (final.loc[con_previa, "hist_fecha_ultima_pelea"] < final.loc[con_previa, "fecha"]).all()
    assert (final.loc[~con_previa, "hist_peleas"] == 0).all()


def test_historial_primera_pelea_topuria_es_anterior_a_2020_10_10(final):
    t = final[final["peleador_url"] == TOPURIA].sort_values("fecha")
    primera = t.iloc[0]
    assert primera["fecha"] == "2020-10-10"
    assert primera["hist_peleas"] == 0
    assert bool(primera["hist_es_debut"]) is True
    assert pd.isna(primera["hist_fecha_ultima_pelea"])
    assert pd.isna(primera["hist_sig_conectados_min"])
    # El rival sí tiene historial, y debe ser anterior a la fecha de la pelea.
    assert primera["rival_hist_fecha_ultima_pelea"] < "2020-10-10"


def test_historial_topuria_antes_de_gaethje(final):
    fila = final[(final["peleador_url"] == TOPURIA) & (final["id_pelea"] == PELEA_GAETHJE)].iloc[0]
    assert fila["fecha"] == "2026-06-14"  # D-01
    assert (fila["hist_peleas"], fila["hist_victorias"], fila["hist_derrotas"]) == (9, 9, 0)
    assert fila["hist_racha"] == 9
    assert fila["hist_fecha_ultima_pelea"] == "2025-06-28"
    assert fila["hist_dias_desde_ultima"] == 351
    assert fila["objetivo_gana"] == 0


# --------------------------------------------------------------------------- cuotas


def test_topuria_gaethje_tiene_cuota_de_cierre(final):
    fila = final[(final["peleador_url"] == TOPURIA) & (final["id_pelea"] == PELEA_GAETHJE)].iloc[0]
    assert fila["cuota_fuente"] == "F-05"
    assert pd.notna(fila["p_cierre_peleador"])
    assert 0.75 < fila["p_cierre_peleador"] < 0.85
    assert "Kalshi" not in fila["cuota_casas"] and "Polymarket" not in fila["cuota_casas"]
    assert fila["cuota_ids_origen"].startswith("F-05:")


def test_todas_las_peleas_de_topuria_tienen_cuota(final):
    t = final[final["peleador_url"] == TOPURIA]
    assert len(t) == 10
    assert t["p_cierre_peleador"].notna().all()


def test_ufc298_usa_f07_por_fight_url(final):
    fila = final[(final["peleador_url"] == TOPURIA) & (final["id_pelea"] == PELEA_UFC298)].iloc[0]
    assert fila["cuota_fuente"] == "F-07"  # D-10: F-05 no tiene la pelea
    bruta_t, bruta_v = 1 / 2.2, 1 / 1.704225
    assert fila["p_cierre_peleador"] == pytest.approx(bruta_t / (bruta_t + bruta_v), abs=1e-6)


def test_d11_excluye_mercados_de_prediccion_e_intercambio(resultado):
    t13 = pd.read_csv(rutas.INTERIM / "t13_f05_moneyline.csv", usecols=["bookmaker"])
    assert not t13["bookmaker"].isin(["Kalshi", "Polymarket"]).any()
    t15 = pd.read_csv(rutas.INTERIM / "t15_f07_filtrado.csv", usecols=["source"])
    assert not (t15["source"] == "Betfair").any()
    assert (t15["source"] == "Betfair Sportsbook").any()


def test_probabilidades_por_pelea_suman_uno(final):
    con = final[final["p_cierre_peleador"].notna()]
    assert ((con["p_cierre_peleador"] + con["p_cierre_rival"]).round(9) == 1).all()
    por_pelea = con.groupby("id_pelea")["p_cierre_peleador"].sum().round(9)
    assert (por_pelea == 1).all()


# --------------------------------------------------------------------------- trazabilidad


def test_source_row_lleva_a_la_fila_exacta_de_raw(final):
    fila = final[(final["peleador_url"] == TOPURIA) & (final["id_pelea"] == PELEA_GAETHJE)].iloc[0]
    with open(rutas.RAIZ / fila["source_file"], newline="", encoding="utf-8") as fh:
        lector = csv.DictReader(fh)
        for i, registro in enumerate(lector, start=1):
            if i == fila["source_row"]:
                break
    assert registro["fight_url"].endswith(PELEA_GAETHJE)
    assert registro["event_date"] == "2026-06-14"
    with open(rutas.RAIZ / fila["source_file"], encoding="utf-8") as fh:
        linea = fh.readlines()[int(fila["source_line"]) - 1]
    assert linea.startswith(registro["event_name"])


def test_cuota_ids_origen_llevan_a_filas_de_f05(final):
    fila = final[(final["peleador_url"] == TOPURIA) & (final["id_pelea"] == PELEA_GAETHJE)].iloc[0]
    filas = [int(x) for x in fila["cuota_ids_origen"].removeprefix("F-05:").split(";")]
    odds = pd.read_csv(rutas.RAW / "archangel0x01_v3/odds.csv")
    usadas = odds.iloc[[f - 1 for f in filas]]
    assert set(usadas["market"]) == {"moneyline"}
    assert usadas["fight_id"].nunique() == 1
    assert set(usadas["bookmaker"]).isdisjoint({"Kalshi", "Polymarket"})


def test_diccionario_cubre_todas_las_columnas(final):
    dic = pd.read_csv(rutas.DICCIONARIO)
    assert list(dic["columna"]) == list(final.columns)
    assert dic[["tipo", "descripcion", "origen"]].notna().all().all()
    construir_diccionario(final)  # no lanza


# --------------------------------------------------------------------------- D-18, D-23, D-24


def test_d18_marca_carga_historica_en_topuria(final):
    t = final[final["peleador_url"] == TOPURIA].set_index("rival_nombre")
    for rival in ("Youssef Zalal", "Damon Jackson", "Alexander Volkanovski"):
        assert bool(t.loc[rival, "cuota_carga_historica"]) is True, rival
    assert bool(t.loc["Justin Gaethje", "cuota_carga_historica"]) is False
    otras = t.drop(index=["Youssef Zalal", "Damon Jackson", "Alexander Volkanovski"])
    assert not otras["cuota_carga_historica"].astype(bool).any()


def test_d18_marca_solo_en_cuotas_f07(final):
    marcadas = final[final["cuota_carga_historica"].astype(bool)]
    assert len(marcadas) > 0
    assert (marcadas["cuota_fuente"] == "F-07").all()
    assert marcadas["cuota_casas"].str.contains("zewnetrzne").all()
    assert not final.loc[final["cuota_fuente"] != "F-07", "cuota_carga_historica"].astype(bool).any()


def test_d23_edad_de_topuria_a_la_fecha_de_la_pelea(final):
    fila = final[(final["peleador_url"] == TOPURIA) & (final["id_pelea"] == PELEA_GAETHJE)].iloc[0]
    dob = pd.Timestamp("1997-01-21")  # F-01, f_*_fighter_dob de Topuria
    esperada = (pd.Timestamp("2026-06-14") - dob).days / 365.25
    assert fila["edad"] == pytest.approx(esperada)
    hoy = (pd.Timestamp.today().normalize() - dob).days / 365.25
    assert fila["edad"] < hoy
    assert fila["altura_cm"] == pytest.approx(170.18)
    assert fila["alcance_cm"] == pytest.approx(175.26)
    assert fila["dif_edad"] == pytest.approx(fila["edad"] - fila["rival_edad"])
    primera = final[final["peleador_url"] == TOPURIA].sort_values("fecha").iloc[0]
    assert primera["edad"] == pytest.approx((pd.Timestamp("2020-10-10") - dob).days / 365.25)


def test_d23_edad_sin_fuga_y_sin_imputacion(final):
    con = final.dropna(subset=["edad"])
    # La edad crece con la fecha: es la de cada pelea, no la actual.
    por_peleador = con.sort_values("fecha").groupby("peleador_url")["edad"]
    assert (por_peleador.diff().dropna() >= 0).all()
    assert (con["edad"] > 0).all()
    t07 = pd.read_csv(rutas.INTERIM / "t07_peleas_f01.csv", low_memory=False)
    faltan_dob = int(t07["f_1_fighter_dob"].isna().sum() + t07["f_2_fighter_dob"].isna().sum())
    assert int(final["edad"].isna().sum()) == faltan_dob
    excluidas = [c for c in t07.columns if c.startswith(("f_1_fighter_", "f_2_fighter_"))]
    assert sorted(excluidas) == sorted(f"f_{i}_fighter_{a}" for i in (1, 2) for a in ("dob", "height_cm", "reach_cm"))


def test_sin_marcadores_provisionales():
    for ruta in (rutas.RAIZ / "src").rglob("*.py"):
        assert "PROVISIONAL" not in ruta.read_text(encoding="utf-8"), ruta
    assert "PROVISIONAL" not in rutas.BITACORA.read_text(encoding="utf-8")
