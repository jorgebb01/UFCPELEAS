"""Utilidades compartidas por los controladores: aviso de salidas ausentes."""

from __future__ import annotations

from flask import render_template, request

from ufcpeleas.models import auditoria


def comprobar_salidas():
    """before_request: si faltan salidas del pipeline, muestra el aviso en lugar de la página."""
    if request.endpoint == "static":
        return None
    faltan = auditoria.salidas_faltantes()
    if faltan:
        return render_template("aviso.html", faltan=faltan), 503
    return None
