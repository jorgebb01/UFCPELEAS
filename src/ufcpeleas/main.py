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
    print("Modelo (test 2025-2026):")
    print(r.modelo["t26"][["modelo", "C", "log_loss", "brier", "accuracy", "ece", "dif_log_loss_vs_mercado", "dif_ic95_inf", "dif_ic95_sup", "elegido"]].to_string(index=False))
    print("Escenarios:")
    print(r.modelo["t29"][["escenario", "modelo", "p_topuria", "ic_inf", "ic_sup", "elegido"]].to_string(index=False))
    print(f"Cifras: {len(r.cifras)} en final/cifras.csv; linaje en final/linaje.csv")
    print(f"Bitácora: {rutas.relativa(rutas.BITACORA)}; diccionario: {rutas.relativa(rutas.DICCIONARIO)}")
    return _informe()


def _informe() -> int:
    """Genera final/informe_ejecutivo.md con las cifras de final/cifras.csv."""
    from ufcpeleas.models.informe import ErrorInforme, generar

    try:
        salida = generar()
    except ErrorInforme as e:
        print(f"ERROR en el informe: {e}", file=sys.stderr)
        return 1
    print(f"Informe: {rutas.relativa(salida)}")
    return 0


def _linaje(nodo: str) -> int:
    """Lista las cifras que cambian si la transformación o fuente `nodo` tiene un error."""
    from ufcpeleas.models.cifras import cifras_afectadas

    afectadas = cifras_afectadas(nodo)
    print(f"{len(afectadas)} cifras dependen de {nodo}:")
    for c in afectadas.itertuples():
        print(f"  {c.id_cifra} [{c.transformacion}] {c.descripcion} = {c.valor}")
    return 0


def _app(host: str, port: int) -> int:
    """Arranca la app Flask del simulacro de auditoría (solo lectura)."""
    from ufcpeleas.app import create_app

    create_app().run(host=host, port=port, debug=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Analiza los argumentos y ejecuta la orden pedida."""
    parser = argparse.ArgumentParser(prog="ufcpeleas", description="Caso CD-726-017: pipeline trazable de datos UFC.")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("pipeline", help="Verifica las fuentes y regenera interim/, final/ (datos, modelo, escenarios, cifras y linaje), bitacora.csv (T-07+) y diccionario.csv")
    sub.add_parser("verificar", help="Solo el paso 0: verifica SHA-256, bytes y registros de registro_fuentes.csv")
    p_lin = sub.add_parser("linaje", help="Cifras de final/cifras.csv que dependen de una transformación (T-07) o fuente (F-05)")
    p_lin.add_argument("nodo", help="ID de transformación o fuente, p. ej. T-07")
    sub.add_parser("informe", help="Genera final/informe_ejecutivo.md desde docs/informe_plantilla.md y final/cifras.csv")
    p_app = sub.add_parser("app", help="Arranca la app web de auditoría (solo lectura) en http://127.0.0.1:5000")
    p_app.add_argument("--host", default="127.0.0.1")
    p_app.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)
    if args.orden == "app":
        return _app(args.host, args.port)
    if args.orden == "pipeline":
        return _pipeline()
    if args.orden == "informe":
        return _informe()
    if args.orden == "linaje":
        return _linaje(args.nodo)
    return _verificar()


if __name__ == "__main__":
    sys.exit(main())
