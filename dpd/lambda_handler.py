"""Lambda handler — Payments Expand.

Entry point para AWS Lambda. Escucha la SQS de entrada, calcula los
productos solicitados y publica la respuesta en SNS.

Variables de entorno requeridas:
    SNS_RESPONSE_TOPIC_ARN   ARN del SNS topic de respuesta
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD   acceso MySQL (VPC)

Flujo por mensaje:
    1. Parsear mensaje SQS → InboundMessage
    2. Leer loan tape desde S3 (input_file)
    3. Leer scheduled_payments_installments + payment_tape desde MySQL
    4. Calcular productos según metadata.products
    5. Escribir loan tape enriquecido en S3 (output_file)
    6. Publicar respuesta en SNS con MessageAttributes
"""
from __future__ import annotations

import logging
from datetime import date

from .db_reader import read_last_dates, read_payments, read_schedule
from .models import InboundMessage, OutboundMessage
from .products import dpd as product_dpd
from .products import total_amount as product_total_amount
from .products import vpn as product_vpn
from .s3_io import read_loan_tape, write_loan_tape
from .sns_publisher import publish_response

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

SUPPORTED_PRODUCTS = {"dpd", "total_amount", "vpn"}


def _validate(msg: InboundMessage) -> None:
    unknown = set(msg.metadata.products) - SUPPORTED_PRODUCTS
    if unknown:
        raise ValueError(f"Productos desconocidos: {unknown}. Soportados: {SUPPORTED_PRODUCTS}")

    if "vpn" in msg.metadata.products and msg.metadata.interest_rate is None:
        log.warning("'vpn' solicitado pero interest_rate no fue provisto — VPN sin descuento.")


def _process_message(msg: InboundMessage) -> None:
    log.info(
        "job_id=%s | products=%s | company=%s | key=%s",
        msg.job_id, msg.metadata.products, msg.target_id, msg.key,
    )

    # 1. Leer loan tape desde S3
    loan_tape = read_loan_tape(msg.input_file)
    log.info("Loan tape cargado: %d filas", len(loan_tape))

    # 2. Leer datos de MySQL
    # company_code y company_id pueden diferir — por ahora usamos target_id para ambos.
    # TODO: cuando el mensaje diferencie company_code de company_id, actualizar.
    spi_df = read_schedule(company_code=msg.target_id)
    payments_df = read_payments(company_id=msg.target_id)
    log.info("DB: %d cuotas | %d pagos", len(spi_df), len(payments_df))

    calc_date = date.today()

    # 3. Calcular productos solicitados
    if "dpd" in msg.metadata.products:
        loan_tape = product_dpd.compute(
            loan_tape=loan_tape,
            spi_df=spi_df,
            payments_df=payments_df,
            key=msg.key,
            calc_date=calc_date,
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

    # 4. Escribir output en S3
    write_loan_tape(loan_tape, msg.output_file)
    log.info("Output escrito en %s", msg.output_file)

    # 5. Construir y publicar respuesta
    last_dates = read_last_dates(
        company_code=msg.target_id,
        company_id=msg.target_id,
    )

    response = OutboundMessage.from_inbound(msg)
    response.metadata.last_payment_tape_date = last_dates["last_payment_tape_date"]
    response.metadata.last_schedule_payment_date = last_dates["last_schedule_payment_date"]
    response.metadata.last_payment_date = last_dates["last_payment_date"]

    message_id = publish_response(response)
    log.info("Respuesta publicada en SNS. MessageId=%s", message_id)


def handler(event: dict, context) -> dict:
    """Entry point de AWS Lambda."""
    records = event.get("Records", [])
    log.info("Recibidos %d records SQS", len(records))

    errors = []
    for record in records:
        try:
            msg = InboundMessage.from_sqs_record(record)
            _validate(msg)
            _process_message(msg)
        except Exception as exc:
            log.exception("Error procesando record: %s", exc)
            errors.append(str(exc))

    if errors:
        # Relanzar para que SQS reintente el batch si hubo errores
        raise RuntimeError(f"Errores en {len(errors)} records: {errors}")

    return {"statusCode": 200, "processed": len(records)}
