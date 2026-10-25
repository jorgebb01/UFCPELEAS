"""Controlador de auditoría: fichas de cifras, cifra al azar, linaje inverso, tablas y filas crudas."""

from __future__ import annotations

import random

from flask import Blueprint, abort, redirect, render_template, request, send_file, url_for

from ufcpeleas.models import auditoria

bp = Blueprint("auditoria", __name__)


def _pagina() -> int:
    """Número de página de la petición (1 por defecto)."""
    return request.args.get("pagina", default=1, type=int) or 1


@bp.get("/cifras")
def cifras():
    """Lista de todas las cifras citables."""
    return render_template("cifras.html", cifras=auditoria.lista_cifras().to_dict("records"))


@bp.get("/cifra/<id_cifra>")
def ficha(id_cifra: str):
    """Ficha de una cifra: valor, fila localizada, transformación, linaje y filas crudas de origen."""
    c = auditoria.cifra(id_cifra)
    if c is None:
        abort(404)
    return render_template(
        "cifra.html",
        c=c,
        loc=auditoria.localizar(c),
        transformacion=auditoria.fila_bitacora(c["transformacion"]),
        linaje=auditoria.linaje_de(id_cifra),
        origen=auditoria.resolver_origen(c, _pagina()),
    )


@bp.get("/cifra-al-azar")
def azar():
    """Simulacro: redirige a la ficha de una cifra elegida al azar; `?semilla=n` repite una elección concreta (D-34)."""
    semilla = request.args.get("semilla", type=int)
    rng = random.Random(semilla) if semilla is not None else None
    return redirect(url_for("auditoria.ficha", id_cifra=auditoria.cifra_al_azar(rng)))


@bp.get("/linaje")
def linaje_indice():
    """Índice de transformaciones y fuentes para el linaje inverso."""
    nodo = request.args.get("nodo", "").strip().upper()
    if nodo:
        return redirect(url_for("auditoria.linaje", nodo=nodo))
    return render_template("linaje_indice.html", bitacora=auditoria.bitacora())


@bp.get("/linaje/<nodo>")
def linaje(nodo: str):
    """Pregunta 4: cifras que cambian si la transformación o fuente `nodo` tiene un error."""
    if not auditoria.es_nodo(nodo):
        abort(404)
    return render_template(
        "linaje.html",
        nodo=nodo,
        cifras=auditoria.afectadas(nodo).to_dict("records"),
        total=len(auditoria.lista_cifras()),
        transformacion=auditoria.fila_bitacora(nodo),
    )


@bp.get("/tabla/<path:archivo>")
def tabla(archivo: str):
    """Vista paginada de un CSV de interim/ o final/."""
    ruta = auditoria.ruta_segura(archivo)
    if ruta is None:
        abort(404)
    columnas, filas, total, pagina, paginas = auditoria.pagina_tabla(ruta, _pagina())
    return render_template("tabla.html", archivo=archivo, columnas=columnas, filas=filas, total=total, pagina=pagina, paginas=paginas)


@bp.get("/fuente/<id_fuente>/fila/<int:source_row>")
def fila(id_fuente: str, source_row: int):
    """Registro exacto de un archivo de raw/ o manual/."""
    if not auditoria.es_nodo(id_fuente):
        abort(404)
    f = auditoria.fila_cruda(id_fuente, source_row)
    if f is None:
        abort(404)
    if "url" in f.campos:
        f.extra = auditoria.captura_de(f.campos["url"])
    return render_template("fila_cruda.html", f=f)


@bp.get("/captura/<nombre>")
def captura(nombre: str):
    """Captura HTML de manual/capturas/ servida como texto (no se ejecuta en el navegador)."""
    ruta = auditoria.ruta_captura(nombre)
    if ruta is None:
        abort(404)
    resp = send_file(ruta, mimetype="text/plain; charset=utf-8", conditional=True)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
