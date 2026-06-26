"""Entry point para el job de AWS Batch — Payments Expand.

Ejecuta el mismo procesamiento que la Lambda (vía dpd.processor) pero iniciado
desde un job de Batch, no desde un trigger SQS. A diferencia de la Lambda, NO
re-evalúa el umbral de derivación a Batch — procesa siempre inline, por lo que
nunca vuelve a encolar otro job (evita el bucle infinito de jobs). El payload del
evento se recibe por variable de entorno DPD_BATCH_PAYLOAD o por argumento --payload.

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
from .processor import process_message, _validate


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

    payload_source = "--payload arg" if args.payload else "DPD_BATCH_PAYLOAD env"
    raw = args.payload or os.environ.get("DPD_BATCH_PAYLOAD")

    log.info(
        "[START] batch_handler | env=%s | region=%s | queue=%s | job_definition=%s",
        os.environ.get("ENVIRONMENT", "unknown"),
        os.environ.get("AWS_REGION", "unknown"),
        os.environ.get("BATCH_JOB_QUEUE", "unknown"),
        os.environ.get("BATCH_JOB_DEFINITION", "unknown"),
    )

    if not raw:
        log.error("[ERROR] batch_handler | payload no recibido — se requiere --payload o DPD_BATCH_PAYLOAD")
        return 1

    log.info("batch_handler | payload_source=%s | payload_size=%d bytes", payload_source, len(raw))

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("[ERROR] batch_handler | payload JSON inválido — %s", exc)
        return 1

    record = {"body": json.dumps(payload)}

    try:
        msg = InboundMessage.from_sqs_record(record)
    except Exception as exc:
        log.error("[ERROR] batch_handler | no se pudo parsear el mensaje — %s", exc)
        return 1

    log.info(
        "batch_handler | job_id=%s | company=%s | products=%s | input=%s | output=%s | rate_type=%s",
        msg.job_id, msg.target_id, msg.metadata.products,
        msg.input_file, msg.output_file, msg.rate_type,
    )

    try:
        _validate(msg)
        process_message(msg)
    except Exception as exc:
        log.exception("[ERROR] batch_handler | job_id=%s — %s", msg.job_id, exc)
        return 1

    log.info("[END] batch_handler | job_id=%s | status=ok", msg.job_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
