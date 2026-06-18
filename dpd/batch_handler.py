"""Entry point para el job de AWS Batch — Payments Expand.

Ejecuta el mismo flujo que lambda_handler._process_message pero iniciado
desde un job de Batch, no desde un trigger SQS. El payload del evento se
recibe por variable de entorno DPD_BATCH_PAYLOAD o por argumento --payload.

Uso:
    python -m dpd.batch_handler --payload '{"origin": "ENRICHER", ...}'
    DPD_BATCH_PAYLOAD='{"origin": "ENRICHER", ...}' python -m dpd.batch_handler
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

log = logging.getLogger(__name__)

from .models import InboundMessage
from .lambda_handler import _process_message, _validate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Ejecuta el flujo DPD desde un job de AWS Batch."
    )
    p.add_argument(
        "--payload",
        default=None,
        help="JSON string con la estructura del InboundMessage. "
             "Si se omite, se lee de la variable de entorno DPD_BATCH_PAYLOAD.",
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    raw = args.payload or os.environ.get("DPD_BATCH_PAYLOAD")
    if not raw:
        print(
            "Error: se requiere --payload o la variable de entorno DPD_BATCH_PAYLOAD.",
            file=sys.stderr,
        )
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: payload JSON inválido — {exc}", file=sys.stderr)
        return 1

    record = {"body": json.dumps(payload)}
    msg = InboundMessage.from_sqs_record(record)
    log.info("Batch handler iniciado | job_id=%s | company_id=%s", msg.job_id, msg.target_id)

    _validate(msg)
    _process_message(msg)
    log.info("Batch handler finalizado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
