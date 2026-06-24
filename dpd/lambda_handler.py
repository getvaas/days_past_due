"""Lambda handler — Payments Expand.

Entry point para AWS Lambda. Escucha la SQS de entrada, calcula los
productos solicitados y publica la respuesta en SNS.

Variables de entorno requeridas:
    SNS_RESPONSE_TOPIC_ARN   ARN del SNS topic de respuesta
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD   acceso MySQL (VPC)

Flujo por mensaje:
    1. Parsear mensaje SQS → InboundMessage
    2. Leer loan tape (input) + output previo (si existe) desde S3
    3. Leer scheduled_payments_installments + payment_tape desde MySQL
    4. Calcular productos según metadata.products
    5. Agregar columnas de trazabilidad (last_update_date, payment_tape_ref)
    6. Escribir loan tape enriquecido en S3 (output_file)
    7. Publicar respuesta en SNS con MessageAttributes
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from . import config
from .batch_submitter import submit_job
from .db_reader import read_last_dates
from .excel_runner import load_payment_tape, load_schedule
from .models import InboundMessage, OutboundMessage
from .products import dpd as product_dpd
from .products import total_amount as product_total_amount
from .products import vpn as product_vpn
from .utils.s3 import read_loan_tape, try_read_loan_tape, write_loan_tape
from .sns_publisher import publish_response
from .spi_builder import LoanTapeColumns, build_and_persist

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

SUPPORTED_PRODUCTS = {"dpd", "total_amount", "vpn"}


def _validate(msg: InboundMessage) -> None:
    unknown = set(msg.metadata.products) - SUPPORTED_PRODUCTS
    if unknown:
        raise ValueError(f"Productos desconocidos: {unknown}. Soportados: {SUPPORTED_PRODUCTS}")

    if "vpn" in msg.metadata.products and msg.metadata.interest_rate is None:
        log.warning("'vpn' solicitado pero interest_rate no fue provisto — VPN sin descuento.")

    if msg.rate_type not in ("fixed", "variable"):
        raise ValueError(f"rate_type inválido: {msg.rate_type!r}. Valores válidos: 'fixed', 'variable'.")


def _process_message(msg: InboundMessage) -> None:
    log.info(
        "[START] job_id=%s | products=%s | company=%s | key=%s | rate_type=%s",
        msg.job_id, msg.metadata.products, msg.target_id, msg.key, msg.rate_type,
    )

    # 1. Leer loan tape desde S3
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

    # 2. Leer datos de payments_db usando company_id directo desde el evento.
    company_id = msg.target_id

    spi_df = load_schedule(company_id)
    payments_df = load_payment_tape(company_id)
    log.info("DB: %d cuotas | %d pagos", len(spi_df), len(payments_df))

    ##TODO A chequear cuando hagamos VPN
    if spi_df.empty:
        if msg.rate_type == "variable":
            # Tasa variable: no se puede generar el SPI automáticamente.
            # Debe existir en BD y cargarse manualmente.
            raise NotImplementedError(
                f"company={msg.target_id}: no hay SPI en BD y rate_type='variable'. "
                "El SPI debe ser cargado manualmente antes de invocar esta Lambda."
            )
        # Tasa fija: construir SPI desde el loan tape y persistirlo en MySQL.
        # La tasa de interés se toma del loan tape (columna interest_rate, por contrato),
        # NO del metadata del mensaje (esa tasa es del tranche, para VPN).
        # Si el loan tape no tiene las columnas requeridas, el build_and_persist
        # lanzará ValueError con los detalles.
        log.info(
            "SPI vacío para company=%s — generando desde loan tape (rate_type=fixed)",
            msg.target_id,
        )
        spi_df = build_and_persist(
            loan_tape=loan_tape,
            company_id=company_id,
            columns=LoanTapeColumns(),
        )
        log.info("SPI generado y persistido: %d cuotas", len(spi_df))

    calc_date = msg.metadata.calc_date or date.today()

    # 3. Calcular productos solicitados
    if "dpd" in msg.metadata.products:
        loan_tape = product_dpd.compute(
            loan_tape=loan_tape,
            spi_df=spi_df,
            payments_df=payments_df,
            key=msg.key,
            calc_date=calc_date,
            paid_threshold=msg.metadata.paid_threshold
        )
        log.info("DPD calculado")

    if "total_amount" in msg.metadata.products:
        loan_tape = product_total_amount.compute(
            loan_tape=loan_tape,
            payments_df=payments_df,
            key=msg.key,
        )
        log.info("total_amount calculado")

    if "vpn" in msg.metadata.products:
        loan_tape = product_vpn.compute(
            loan_tape=loan_tape,
            spi_df=spi_df,
            key=msg.key,
            interest_rate=msg.metadata.interest_rate,
            calc_date=calc_date,
        )
        log.info("VPN calculado")

    # 4. Columnas de trazabilidad
    loan_tape["last_update_date"] = datetime.now(tz=timezone.utc).isoformat()
    loan_tape["payment_tape_ref"] = msg.job_id

    # 5. Escribir output en S3
    write_loan_tape(loan_tape, msg.output_file)
    log.info("Output escrito en %s", msg.output_file)

    # 6. Construir y publicar respuesta
    last_dates = read_last_dates(company_id=company_id)

    response = OutboundMessage.from_inbound(msg)
    response.metadata.last_payment_tape_date = last_dates["last_payment_tape_date"]
    response.metadata.last_schedule_payment_date = last_dates["last_schedule_payment_date"]
    response.metadata.last_payment_date = last_dates["last_payment_date"]

    message_id = publish_response(response)
    log.info(
        "[END] job_id=%s | output=%s | sns_message_id=%s",
        msg.job_id, msg.output_file, message_id,
    )


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
