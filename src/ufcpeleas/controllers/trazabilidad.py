"""Controlador de trazabilidad: fuentes con verificación de hashes en vivo, bitácora y decisiones."""

from __future__ import annotations

from flask import Blueprint, render_template

from ufcpeleas.models import auditoria

bp = Blueprint("trazabilidad", __name__)


@bp.get("/fuentes")
def fuentes():
    """registro_fuentes.csv con SHA-256, bytes y registros comprobados ahora (paso 0 sin escribir)."""
    estados, capturas, error = auditoria.estado_fuentes()
    return render_template("fuentes.html", estados=estados, capturas=capturas, error=error)


@bp.get("/bitacora")
def bitacora():
    """bitacora.csv completa, con anclas por transformación y decisiones enlazadas."""
    return render_template("bitacora.html", filas=auditoria.bitacora())


@bp.get("/decisiones")
def decisiones():
    """decisiones.md con un ancla por decisión."""
    html, ids = auditoria.decisiones_html()
    return render_template("decisiones.html", html=html, ids=ids)
