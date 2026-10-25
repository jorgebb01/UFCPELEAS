"""UFCPELEAS: análisis de peleas de UFC (patrón MVC)."""

from __future__ import annotations


def create_app(config: dict | None = None):
    """Application factory (importación diferida: los modelos no cargan Flask). Uso: `flask --app ufcpeleas run`."""
    from ufcpeleas.app import create_app as _crear

    return _crear(config)
