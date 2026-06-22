"""Runner local — emula la llegada de un evento SQS a la Lambda.

Permite ejecutar el flujo completo de `lambda_handler` desde la línea de comandos
sin necesidad de un trigger SQS real. Útil para desarrollo y debugging.

Uso:
    # Con el evento hardcodeado en DEFAULT_EVENT (editá este archivo):
    python -m dpd.local_runner
    python -m dpd.local_runner --dry-run

    # Con un archivo JSON externo:
    python -m dpd.local_runner --event evento.json
    python -m dpd.local_runner --event evento.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .lambda_handler import handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

log = logging.getLogger(__name__)

# ── Evento hardcodeado para ejecución local sin argumentos ───────────────────
# Editá estos valores antes de correr `python -m dpd.local_runner`.
DEFAULT_EVENT = {
    "origin": "ENRICHER",
    "target": "PAYMENTS_EXPAND",
    "job_id": "local-test-001",
    "input_file": "s3://mi-bucket/loan_tape.csv",
    "output_file": "s3://mi-bucket/output.csv",
    "key": "borrower_contract_id",
    "target_type": "COMPANY",
    "target_id": 143,
    "rate_type": "fixed",
    "metadata": {
        "products": ["dpd"],
        "paid_threshold": 1.0,
    },
}
# ────────────────────────────────────────────────────────────────────────────


def _build_sqs_event(payload: dict) -> dict:
    """Construye un evento SQS sintético con un solo record."""
    return {
        "Records": [
            {"body": json.dumps(payload)}
        ]
    }


def run(payload: dict) -> dict:
    """Ejecuta lambda_handler.handler() con el payload dado.

    Returns:
        El dict de respuesta del handler (statusCode, processed).
    """
    log.info(
        "job_id=%s | company_id=%s | products=%s",
        payload.get("job_id"), payload.get("target_id"),
        payload.get("metadata", {}).get("products"),
    )
    event = _build_sqs_event(payload)
    return handler(event, context=None)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Ejecuta el flujo de la Lambda localmente. "
                    "Sin --event usa el DEFAULT_EVENT hardcodeado en este archivo."
    )
    p.add_argument(
        "--event", default=None,
        help="Ruta al archivo JSON con la estructura del mensaje SQS. "
             "Si se omite, usa DEFAULT_EVENT definido en local_runner.py.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Valida y parsea el evento sin ejecutar el flujo.",
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    if args.event:
        path = Path(args.event)
        if not path.is_file():
            print(f"Error: archivo no encontrado: {args.event!r}", file=sys.stderr)
            return 1
        payload = json.loads(path.read_text())
        log.info("Evento cargado desde %s", path)
    else:
        payload = DEFAULT_EVENT
        log.info("Usando DEFAULT_EVENT hardcodeado en local_runner.py")

    if args.dry_run:
        from .models import InboundMessage
        msg = InboundMessage.from_sqs_record({"body": json.dumps(payload)})
        print("Dry-run OK — evento válido:")
        print(f"  job_id     : {msg.job_id}")
        print(f"  target_id  : {msg.target_id}")
        print(f"  input_file : {msg.input_file}")
        print(f"  output_file: {msg.output_file}")
        print(f"  products   : {msg.metadata.products}")
        return 0

    result = run(payload)
    print(f"\nFinalizado: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
