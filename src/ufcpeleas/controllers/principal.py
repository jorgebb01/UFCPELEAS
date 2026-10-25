"""Controlador principal: portada con los escenarios e informe ejecutivo."""

from __future__ import annotations

from flask import Blueprint, render_template, url_for

from ufcpeleas.controllers.comun import comprobar_salidas
from ufcpeleas.models import auditoria

bp = Blueprint("principal", __name__)
bp.before_app_request(comprobar_salidas)


@bp.get("/")
def inicio():
    """Respuesta del caso: probabilidad de Topuria por escenario y modelo."""
    return render_template("inicio.html", escenarios=auditoria.escenarios())


@bp.get("/informe")
def informe():
    """Informe ejecutivo con cada [C-xxx] enlazado a su ficha."""
    html = auditoria.informe_html(lambda id_c: url_for("auditoria.ficha", id_cifra=id_c))
    return render_template("informe.html", html=html)
