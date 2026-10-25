"""Punto de entrada de línea de órdenes: `uv run ufcpeleas pipeline` regenera todo desde raw/ y manual/."""

from __future__ import annotations

import argparse
import sys

from ufcpeleas.models import rutas
from ufcpeleas.models.fuentes import ErrorVerificacion


def _verificar() -> int:
    """Ejecuta solo el paso 0 (hashes, bytes y registros de las fuentes)."""
    from ufcpeleas.models.pipeline import paso0_verificar

    try:
        verificaciones = paso0_verificar()
    except ErrorVerificacion as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Paso 0: {len(verificaciones)} archivos verificados (SHA-256, bytes y registros) -> final/verificacion_fuentes.csv")
    return 0


def _pipeline() -> int:
    """Ejecuta el pipeline completo e imprime el resumen."""
    from ufcpeleas.models.pipeline import ejecutar

    try:
        r = ejecutar()
    except ErrorVerificacion as e:
        print(f"ERROR en el paso 0, no se transforma nada: {e}", file=sys.stderr)
        return 1
    print(f"Paso 0: {len(r.verificaciones)} archivos verificados (SHA-256, bytes y registros).")
    print("Transformaciones:")
    for e in r.contexto.bitacora.entradas:
        print(f"  {e.id}: {e.filas_antes} -> {e.filas_despues}  {e.salida}")
    print("Controles:")
    for a in r.contexto.avisos:
        print(f"  {a}")
    print("Cobertura de cuotas de cierre:")
    print(r.cobertura.to_string(index=False))
    print(f"Bitácora: {rutas.relativa(rutas.BITACORA)}; diccionario: {rutas.relativa(rutas.DICCIONARIO)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Analiza los argumentos y ejecuta la orden pedida."""
    parser = argparse.ArgumentParser(prog="ufcpeleas", description="Caso CD-726-017: pipeline trazable de datos UFC.")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("pipeline", help="Verifica las fuentes y regenera interim/, final/, bitacora.csv (T-07+) y diccionario.csv")
    sub.add_parser("verificar", help="Solo el paso 0: verifica SHA-256, bytes y registros de registro_fuentes.csv")
    args = parser.parse_args(argv)
    if args.orden == "pipeline":
        return _pipeline()
    return _verificar()


if __name__ == "__main__":
    sys.exit(main())
