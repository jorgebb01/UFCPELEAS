"""Tests de la app Flask del simulacro de auditoría (solo lectura) con test_client()."""

from __future__ import annotations

import hashlib
import re

import pytest

from ufcpeleas import create_app
from ufcpeleas.models import rutas
from ufcpeleas.models.cifras import CIFRAS, cifras_afectadas
from ufcpeleas.models.pipeline import ejecutar

RUTAS_A_PROBAR = (
    "/",
    "/informe",
    "/cifras",
    "/cifra/C-001",
    "/cifra/C-049",
    "/cifra/C-049?pagina=2",
    "/cifra/C-016",
    "/cifra/C-158",
    "/cifra-al-azar",
    "/linaje",
    "/linaje/T-07",
    "/tabla/interim/t25_predicciones_test.csv?pagina=2",
    "/fuente/F-01/fila/218",
    "/fuente/F-02/fila/157",
    "/captura/heavy_paddy-pimblett-ilia-topuria-ufc-hofer.html",
    "/fuentes",
    "/bitacora",
    "/decisiones",
)


@pytest.fixture(scope="module")
def cliente():
    """Asegura que existen las salidas (pipeline + informe) y devuelve un cliente de pruebas."""
    if not (rutas.FINAL / "informe_ejecutivo.md").exists() or not CIFRAS.exists():
        from ufcpeleas.models.informe import generar

        ejecutar()
        generar()
    return create_app({"TESTING": True}).test_client()


def _huella() -> dict[str, str]:
    """SHA-256 de todos los archivos de datos y trazabilidad del proyecto (fuera de código y cachés)."""
    huella = {}
    for base in (rutas.RAW, rutas.MANUAL, rutas.INTERIM, rutas.FINAL):
        for p in sorted(base.rglob("*")):
            if p.is_file():
                huella[rutas.relativa(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (rutas.BITACORA, rutas.DICCIONARIO, rutas.REGISTRO_FUENTES, rutas.RAIZ / "decisiones.md"):
        huella[rutas.relativa(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return huella


def test_portada(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "revancha_gaethje" in html and "pimblett" in html and "Informe" in html


def test_ficha_c049_valor_y_origen(cliente):
    html = cliente.get("/cifra/C-049").get_data(as_text=True)
    assert "0.688889" in html
    assert "F-07" in html and "F-01" in html
    # La primera fila cruda es la línea de F-07 (BetOnline.ag) leída del archivo original.
    assert "registro 216437" in html and "BetOnline.ag" in html
    assert "El valor del archivo coincide con la cifra" in html


def test_ficha_c001_fila_cruda_f01(cliente):
    html = cliente.get("/cifra/C-001").get_data(as_text=True)
    assert "raw/UFC_full_data_silver_v2.csv" in html
    assert "registro 218" in html and "línea física 228" in html
    assert re.search(r"<th>event_date</th><td>2026-06-14</td>", html)
    assert "T-07" in html


def test_ficha_inexistente_404(cliente):
    assert cliente.get("/cifra/C-999").status_code == 404
    assert cliente.get("/cifra/X").status_code == 404
    assert cliente.get("/tabla/../raw/UFC_full_data_silver_v2.csv").status_code == 404


def test_linaje_t07(cliente):
    html = cliente.get("/linaje/T-07").get_data(as_text=True)
    n = len(cifras_afectadas("T-07"))
    assert n == 161
    assert f"cambian {n} de" in html
    assert len(re.findall(r'href="/cifra/C-\d{3}"', html)) == n


def test_cifra_al_azar_redirige(cliente):
    r = cliente.get("/cifra-al-azar")
    assert r.status_code == 302
    assert re.fullmatch(r"/cifra/C-\d{3}", r.headers["Location"])
    assert cliente.get(r.headers["Location"]).status_code == 200


def test_cifra_al_azar_con_semilla_es_reproducible(cliente):
    """D-34: con ?semilla= la elección se repite; sin semilla no es predecible."""
    destinos = {cliente.get("/cifra-al-azar?semilla=726").headers["Location"] for _ in range(3)}
    assert len(destinos) == 1
    assert re.fullmatch(r"/cifra/C-\d{3}", destinos.pop())


def test_informe_enlaza_cifras(cliente):
    html = cliente.get("/informe").get_data(as_text=True)
    assert 'href="/cifra/C-049"' in html and 'href="/cifra/C-058"' in html


def test_fuentes_verifica_en_vivo(cliente):
    html = cliente.get("/fuentes").get_data(as_text=True)
    assert html.count("correcto") >= 8 and "NO coincide" not in html
    assert "7bdfb1b9feea9bfba1c5eb210028764562673205dbae218118b91a7c73313f67" in html


def test_fila_f02_con_captura_y_hash(cliente):
    html = cliente.get("/fuente/F-02/fila/157").get_data(as_text=True)
    assert "M-0172" in html and "heavy_paddy-pimblett-ilia-topuria-ufc-hofer.html" in html and "SHA-256" in html
    r = cliente.get("/captura/heavy_paddy-pimblett-ilia-topuria-ufc-hofer.html")
    assert r.status_code == 200 and r.mimetype == "text/plain"
    assert cliente.get("/captura/..%2Fcuotas.csv").status_code == 404


def test_la_app_no_escribe_en_disco(cliente):
    antes = _huella()
    for ruta in RUTAS_A_PROBAR:
        assert cliente.get(ruta).status_code in (200, 302), ruta
    assert _huella() == antes


def test_aviso_si_faltan_salidas(monkeypatch):
    from ufcpeleas.models import auditoria

    monkeypatch.setattr(auditoria, "SALIDAS_NECESARIAS", (rutas.FINAL / "no_existe.csv",))
    r = create_app({"TESTING": True}).test_client().get("/")
    assert r.status_code == 503
    assert "uv run ufcpeleas pipeline" in r.get_data(as_text=True)


def test_modelos_no_importan_flask():
    import ast

    for p in (rutas.RAIZ / "src" / "ufcpeleas" / "models").rglob("*.py"):
        arbol = ast.parse(p.read_text(encoding="utf-8"))
        for n in ast.walk(arbol):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                nombres = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                assert not any(x.split(".")[0] == "flask" for x in nombres), p
