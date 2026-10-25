"""Application factory de la app Flask del simulacro de auditoría (solo lectura)."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template

from ufcpeleas.controllers.auditoria import bp as auditoria_bp
from ufcpeleas.controllers.principal import bp as principal_bp
from ufcpeleas.controllers.trazabilidad import bp as trazabilidad_bp

VISTAS = Path(__file__).resolve().parent / "views"


def create_app(config: dict | None = None) -> Flask:
    """Crea la app: registra los Blueprints y apunta plantillas y estáticos a views/."""
    app = Flask(
        __name__,
        template_folder=str(VISTAS / "templates"),
        static_folder=str(VISTAS / "static"),
        instance_relative_config=False,
    )
    app.config.update(JSON_AS_ASCII=False)
    if config:
        app.config.update(config)
    app.register_blueprint(principal_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(trazabilidad_bp)
    app.register_error_handler(404, lambda _e: (render_template("404.html"), 404))
    return app
