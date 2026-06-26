"""Núcleo de procesamiento — Payments Expand.

Lógica compartida entre los dos puntos de entrada (AWS Lambda y AWS Batch).
Calcula los productos solicitados sobre el loan tape y publica la respuesta en SNS.

IMPORTANTE: este módulo NO conoce el umbral de derivación a AWS Batch. La decisión
de derivar a Batch vive exclusivamente en `lambda_handler.handler()`. Así, cuando el
job de Batch ejecuta este procesamiento, lo hace siempre inline y nunca vuelve a
encolar otro job (evita el bucle infinito de jobs).

Flujo por mensaje:
    1. Leer loan tape (input) desde S3
    2. Leer scheduled_payments_installments + payment_tape desde MySQL
    3. Generar SPI desde el loan tape si no existe (solo rate_type=fixed)
    4. Calcular productos según metadata.products
    5. Agregar columnas de trazabilidad (last_update_date, payment_tape_ref)
    6. Escribir loan tape enriquecido en S3 (output_file)
    7. Publicar respuesta en SNS con MessageAttributes
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import polars as pl

from .db_reader import read_last_dates
from .excel_runner import load_payment_tape, load_schedule
from .models import InboundMessage, OutboundMessage
from .products import dpd as product_dpd
from .products import total_amount as product_total_amount
from .products import vpn as product_vpn
from .utils.s3 import read_loan_tape, write_loan_tape
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


def process_message(msg: InboundMessage) -> None:
    """Entry point inline: lee el loan tape desde S3 y lo procesa.

    No deriva a AWS Batch — usado por el job de Batch y por cualquier flujo que ya
    haya decidido procesar inline.
    """
    loan_tape = read_loan_tape(msg.input_file)
    log.info("Loan tape cargado: %d filas", len(loan_tape))
    process_loan_tape(msg, loan_tape)


def process_loan_tape(msg: InboundMessage, loan_tape: pl.DataFrame) -> None:
    """Pipeline completo a partir de un loan tape ya leído (sin chequeo de umbral)."""
    log.info(
        "[START] job_id=%s | products=%s | company=%s | key=%s | rate_type=%s",
        msg.job_id, msg.metadata.products, msg.target_id, msg.key, msg.rate_type,
    )

    # 1. Leer datos de payments_db. Los loaders devuelven pandas → convertir a polars.
    company_id = msg.target_id

    spi_df = pl.from_pandas(load_schedule(company_id))
    payments_df = pl.from_pandas(load_payment_tape(company_id))
    log.info("DB: %d cuotas | %d pagos", len(spi_df), len(payments_df))

    ##TODO A chequear cuando hagamos VPN
    if spi_df.is_empty():
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
        spi_df = pl.from_pandas(build_and_persist(
            loan_tape=loan_tape.to_pandas(),
            company_id=company_id,
            columns=LoanTapeColumns(),
        ))
        log.info("SPI generado y persistido: %d cuotas", len(spi_df))

    calc_date = msg.metadata.calc_date or date.today()

    # 2. Calcular productos — cada compute devuelve solo (key + cols nuevas),
    # sin tocar el loan_tape. Al final un único join contra el loan_tape.
    enrichments: list[pl.DataFrame] = []

    if "dpd" in msg.metadata.products:
        enrichments.append(product_dpd.compute(
            loan_tape=loan_tape,
            spi_df=spi_df,
            payments_df=payments_df,
            key=msg.key,
            calc_date=calc_date,
            paid_threshold=msg.metadata.paid_threshold,
        ))
        log.info("DPD calculado")

    if "total_amount" in msg.metadata.products:
        enrichments.append(product_total_amount.compute(
            loan_tape=loan_tape,
            payments_df=payments_df,
            key=msg.key,
        ))
        log.info("total_amount calculado")

    if "vpn" in msg.metadata.products:
        enrichments.append(product_vpn.compute(
            loan_tape=loan_tape,
            spi_df=spi_df,
            key=msg.key,
            interest_rate=msg.metadata.interest_rate,
            calc_date=calc_date,
        ))
        log.info("VPN calculado")

    # Combinar enrichments entre sí (pequeños) y luego un único join al loan_tape.
    if enrichments:
        combined = enrichments[0]
        for e in enrichments[1:]:
            combined = combined.join(e, on=msg.key, how="left")
        loan_tape = loan_tape.join(combined, on=msg.key, how="left")

    # 3. Columnas de trazabilidad
    loan_tape = loan_tape.with_columns([
        pl.lit(datetime.now(tz=timezone.utc).isoformat()).alias("last_update_date"),
        pl.lit(msg.job_id).alias("payment_tape_ref"),
    ])

    # 4. Escribir output en S3
    write_loan_tape(loan_tape, msg.output_file)
    log.info("Output escrito en %s", msg.output_file)

    # 5. Construir y publicar respuesta
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
