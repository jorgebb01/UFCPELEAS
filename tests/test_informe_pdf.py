"""Tests del PDF del informe (D-35): conserva todos los IDs y números del .md, no añade ninguno y es determinista."""

from __future__ import annotations

import hashlib

import pytest
from pypdf import PdfReader

from ufcpeleas.main import main
from ufcpeleas.models.cifras import CIFRAS
from ufcpeleas.models.informe import INFORME, generar
from ufcpeleas.models.informe_pdf import INFORME_PDF, generar_pdf, texto_pdf, verificar_pdf


@pytest.fixture(scope="module")
def pdf():
    """Genera el PDF desde el .md (y el .md desde el pipeline si aún no existe)."""
    if not INFORME.exists() or not CIFRAS.exists():
        from ufcpeleas.models.pipeline import ejecutar

        ejecutar()
        generar()
    return generar_pdf()


def test_pdf_conserva_ids_y_numeros(pdf):
    c = verificar_pdf(INFORME, pdf)
    assert c.correcta, c
    assert c.ids_md > 100 and c.numeros_md > 100
    assert "C-049" in "".join(texto_pdf(pdf)) and "68,9 % [C-049]" in "".join(texto_pdf(pdf))


def test_pdf_cuerpo_maximo_tres_paginas(pdf):
    c = verificar_pdf(INFORME, pdf)
    assert 1 <= c.paginas_cuerpo <= 3
    assert c.paginas > c.paginas_cuerpo  # el anexo empieza en página nueva


def test_pdf_acentos_y_simbolos(pdf):
    texto = "\n".join(texto_pdf(pdf))
    for fragmento in ["¿Volverá a ganar El Matador?", "Topuria–Pimblett", "[C-058 − C-049]", "≈ 86 %", "año", "Descripción"]:
        assert fragmento in texto, fragmento


def test_pdf_determinista_y_con_hash_del_md(pdf):
    antes = pdf.read_bytes()
    assert generar_pdf().read_bytes() == antes
    sha_md = hashlib.sha256(INFORME.read_bytes()).hexdigest()
    assert sha_md in (PdfReader(INFORME_PDF).metadata.subject or "")


def test_pdf_detecta_cifras_que_no_estan_en_el_md(pdf, tmp_path):
    """Si el .md tuviera una cifra que el PDF no muestra (o al revés), la verificación lo detecta."""
    md = tmp_path / "informe.md"
    md.write_text(INFORME.read_text(encoding="utf-8") + "\nCifra nueva: 12,3 % [C-999]\n", encoding="utf-8")
    c = verificar_pdf(md, pdf)
    assert not c.correcta
    assert c.ids_faltan == ["C-999"] and c.numeros_faltan == ["12,3"]
    recortado = tmp_path / "recortado.md"
    recortado.write_text(INFORME.read_text(encoding="utf-8").replace("68,9 % [C-049]", "[C-049]"), encoding="utf-8")
    c2 = verificar_pdf(recortado, pdf)
    assert "68,9" in c2.numeros_sobran


def test_cli_pdf(pdf, capsys):
    assert main(["pdf"]) == 0
    assert "final/informe_ejecutivo.pdf" in capsys.readouterr().out
