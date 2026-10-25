"""Tests del informe ejecutivo: toda cifra sale de final/cifras.csv con su ID y el informe cabe en 3 páginas."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from ufcpeleas.models.cifras import CIFRAS
from ufcpeleas.models.informe import PLANTILLA, ErrorInforme, formatear, generar, renderizar
from ufcpeleas.models.pipeline import ejecutar


@pytest.fixture(scope="module")
def informe():
    """Pipeline completo y generación del informe."""
    ejecutar()
    return generar().read_text(encoding="utf-8")


def test_informe_sin_marcadores_pendientes(informe):
    assert "{{" not in informe and "}}" not in informe


def test_informe_cita_cifras_existentes_con_su_valor(informe):
    cifras = pd.read_csv(CIFRAS, dtype={"valor": str}).set_index("id_cifra")
    citadas = set(re.findall(r"\[(C-\d{3})", informe))
    assert {"C-049", "C-058", "C-016", "C-002"} <= citadas
    assert citadas <= set(cifras.index)
    assert "68,9 % [C-049]" in informe
    assert formatear(cifras.loc["C-058", "valor"], "pct") + " [C-058]" in informe
    anexo = informe.split("## Anexo: cifras citadas")[1]
    assert set(re.findall(r"^\| (C-\d{3}) \|", anexo, flags=re.M)) == citadas


def test_informe_maximo_tres_paginas(informe):
    cuerpo = informe.split("## Anexo: cifras citadas")[0]
    assert len(cuerpo.split()) <= 1500


def test_informe_numeros_de_resultado_solo_por_marcador():
    """En la plantilla, ningún porcentaje ni decimal se escribe a mano (salvo el '≈ 86 %' citado del caso)."""
    plantilla = re.sub(r"\{\{[^{}]+\}\}", "", PLANTILLA.read_text(encoding="utf-8"))
    sueltos = re.findall(r"\d+,\d+|\d+ ?%", plantilla)
    assert sueltos == ["86 %", "75 %", "85 %"], sueltos


def test_informe_rechaza_cifra_inexistente():
    cifras = pd.read_csv(CIFRAS, dtype={"valor": str})
    with pytest.raises(ErrorInforme):
        renderizar("{{C-999:pct}}", cifras)
