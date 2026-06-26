"""Lambda handler — Payments Expand.

Entry point para AWS Lambda. Escucha la SQS de entrada y, por cada mensaje:
decide si el loan tape es lo bastante grande como para derivar el procesamiento a
AWS Batch; si no, lo procesa inline vía `processor.process_loan_tape`.

La decisión de derivar a Batch vive EXCLUSIVAMENTE aquí. El núcleo de procesamiento
(`dpd.processor`) no conoce el umbral, de modo que el job de Batch procesa siempre
inline y nunca vuelve a encolar otro job (evita el bucle infinito de jobs).

Variables de entorno requeridas:
    SNS_RESPONSE_TOPIC_ARN   ARN del SNS topic de respuesta
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD   acceso MySQL (VPC)
"""
from __future__ import annotations

import logging

from . import config
from .batch_submitter import submit_job
from .models import InboundMessage
from .utils.s3 import read_loan_tape
from . import processor
from .processor import _validate  # re-export para compatibilidad

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def _process_message(msg: InboundMessage) -> None:
    """Procesa un mensaje en el contexto de la Lambda.

    Lee el loan tape y, si supera el umbral, deriva a AWS Batch y retorna. Si no,
    procesa inline reutilizando el tape ya leído (sin doble lectura de S3).
    """
    loan_tape = read_loan_tape(msg.input_file)
    log.info("Loan tape cargado: %d filas", len(loan_tape))

    # Si el loan tape supera el umbral, derivar a AWS Batch y retornar.
    if len(loan_tape) > config.BATCH_ROW_THRESHOLD:
        log.info(
            "Loan tape supera el umbral (%d > %d) — derivando a AWS Batch.",
            len(loan_tape), config.BATCH_ROW_THRESHOLD,
        )
        payload = {
            "origin": msg.origin,
            "target": msg.target,
            "job_id": msg.job_id,
            "input_file": msg.input_file,
            "output_file": msg.output_file,
            "key": msg.key,
            "target_type": msg.target_type,
            "target_id": msg.target_id,
            "rate_type": msg.rate_type,
            "metadata": msg.metadata.to_dict(),
        }
        submit_job(payload, config.BATCH_JOB_QUEUE, config.BATCH_JOB_DEFINITION)
        return

    # Tape bajo el umbral: procesar inline reutilizando el tape ya leído.
    processor.process_loan_tape(msg, loan_tape)


def handler(event: dict, context) -> dict:
    """Entry point de AWS Lambda."""
    records = event.get("Records", [])
    log.info("[START] handler | records=%d", len(records))

    errors = []
    for i, record in enumerate(records, start=1):
        try:
            msg = InboundMessage.from_sqs_record(record)
            _validate(msg)
            _process_message(msg)
        except Exception as exc:
            log.exception("Error en record %d/%d: %s", i, len(records), exc)
            errors.append(str(exc))

    status = "ok" if not errors else f"errors={len(errors)}"
    log.info("[END] handler | processed=%d | %s", len(records), status)

    if errors:
        raise RuntimeError(f"Errores en {len(errors)} records: {errors}")

    return {"statusCode": 200, "processed": len(records)}
