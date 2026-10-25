"""Normalización de nombres (uniones por nombre, D-02) y conversión de cuotas (D-08)."""

from __future__ import annotations

import difflib
import math
import re
import unicodedata

# Correspondencias de letras que NFKD no descompone (ł, ø, ß...).
_LETRAS = str.maketrans({"ł": "l", "Ł": "l", "ø": "o", "Ø": "o", "ß": "ss", "đ": "d", "Đ": "d", "ı": "i"})
_SUFIJOS = re.compile(r"\b(jr|sr|ii|iii|iv)\b")


def normalizar_nombre(nombre: object) -> str:
    """Minúsculas, sin acentos, sin signos ni sufijos (Jr., III); espacios simples."""
    if nombre is None or (isinstance(nombre, float) and math.isnan(nombre)):
        return ""
    s = unicodedata.normalize("NFKD", str(nombre).translate(_LETRAS))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z ]", " ", s)
    s = _SUFIJOS.sub(" ", s)
    return " ".join(s.split())


def similitud_nombres(a: str, b: str) -> int:
    """Nivel de coincidencia entre dos nombres ya normalizados.

    2 = idénticos; 1 = compatibles (uno contiene los tokens del otro, o comparten un token de
    3+ letras y difflib >= 0,6; también nombres pegados como "sumudaerji" / "su mudaerji");
    0 = distintos.
    """
    if not a or not b:
        return 0
    if a == b:
        return 2
    if a.replace(" ", "") == b.replace(" ", ""):
        return 1
    ta, tb = set(a.split()), set(b.split())
    if ta <= tb or tb <= ta:
        return 1
    comunes = {t for t in ta & tb if len(t) >= 3}
    if comunes and difflib.SequenceMatcher(None, a, b).ratio() >= 0.6:
        return 1
    return 0


def americana_a_decimal(valor: object) -> float:
    """D-08: decimal = 1 + A/100 si A > 0 y 1 + 100/|A| si A < 0, redondeado a 4 decimales.

    Acepta texto con signo y comas de miles ("+1,200"); las flechas de BFO se eliminan.
    """
    texto = str(valor).replace(",", "").replace("▲", "").replace("▼", "").strip()
    a = float(texto)
    if a == 0 or abs(a) < 100:
        raise ValueError(f"Cuota americana no válida: {valor!r}")
    dec = 1 + a / 100 if a > 0 else 1 + 100 / abs(a)
    return round(dec, 4)


def prob_implicita(decimal: float) -> float:
    """D-08: probabilidad implícita bruta = 1 / cuota decimal."""
    return 1.0 / decimal


def quitar_margen(p1_bruta: float, p2_bruta: float) -> tuple[float, float, float]:
    """D-08: normalización proporcional de un mercado de dos resultados.

    Devuelve (p1, p2, margen), con margen = p1_bruta + p2_bruta - 1.
    """
    suma = p1_bruta + p2_bruta
    return p1_bruta / suma, p2_bruta / suma, suma - 1.0
