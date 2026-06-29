"""Product: Days Past Due.

Agrega columnas DPD al loan tape por contrato.
Columnas que devuelve:
    dpd_current       — máximo DPD entre cuotas vencidas del contrato
    amount_in_arrears — suma de arrears en cuotas con dpd > 0
"""
from __future__ import annotations

import logging
from datetime import date

import polars as pl

from ..config import RunConfig
from ..modes import cascade_fifo, join_installment

log = logging.getLogger(__name__)


def _installments_from_pl(spi: pl.DataFrame) -> list[dict]:
    date_col = "installment_date" if "installment_date" in spi.columns else "date"
    valid = (
        spi
        .filter(pl.col(date_col).is_not_null() & (pl.col("gross_amount").fill_null(0) > 0))
        .with_columns(pl.col(date_col).alias("installment_date"))
    )
    return [
        {
            "id": r["id"],
            "borrower_contract_id": r["borrower_contract_id"],
            "borrower_installment_reference": r.get("borrower_installment_reference"),
            "installment_date": r["installment_date"],
            "gross_amount": r.get("gross_amount", 0),
            "guarantee_amount": r.get("guarantee_amount", 0),
            "principal_amount": r.get("principal_amount", 0),
            "interest_amount": r.get("interest_amount", 0),
            "tax_amount": r.get("tax_amount", 0),
            "fee_amount": r.get("fee_amount", 0),
        }
        for r in valid.to_dicts()
    ]


def _payments_from_pl(payments: pl.DataFrame) -> list[dict]:
    valid = payments.filter(
        pl.col("payment_date").is_not_null() & (pl.col("total_payment").fill_null(0) > 0)
    )
    return [
        {
            "borrower_contract_id": r["borrower_contract_id"],
            "borrower_installment_reference": r.get("borrower_installment_reference"),
            "payment_date": r["payment_date"],
            "total_payment": r.get("total_payment", 0),
        }
        for r in valid.to_dicts()
    ]


def compute(
    loan_tape: pl.DataFrame,
    spi_df: pl.DataFrame,
    payments_df: pl.DataFrame,
    key: str,
    calc_date: date | None = None,
    grace_days: int = 1,
    mode: str = "cascade",
    paid_threshold: float = 1.0,
) -> pl.DataFrame:
    """Calcula DPD por contrato.

    Devuelve un DataFrame con solo (key, dpd_current, amount_in_arrears) —
    sin copiar el loan_tape. El join al loan_tape lo hace el caller.

    Args:
        loan_tape:      Solo se usa para determinar qué contratos existen (columna key).
        spi_df:         scheduled_payments_installments.
        payments_df:    payment_tape.
        key:            Columna identificadora de contrato en loan_tape.
        calc_date:      Fecha de corte. Default: hoy.
        grace_days:     Días de gracia. Default: 1.
        mode:           "cascade" (default) | "join".
        paid_threshold: Fracción mínima pagada para cuota al día.

    Returns:
        DataFrame con columnas (key, dpd_current, amount_in_arrears).
    """
    if calc_date is None:
        calc_date = date.today()

    log.info(
        "[START] dpd.compute | contracts=%d | mode=%s | calc_date=%s | threshold=%s",
        len(loan_tape), mode, calc_date, paid_threshold,
    )

    cfg = RunConfig(
        company_id=0,
        mode=mode,
        partial_payment_counts=False,
        calculation_date=calc_date,
        grace_days=grace_days,
        paid_threshold=paid_threshold,
    )

    insts = _installments_from_pl(spi_df)
    pays = _payments_from_pl(payments_df)

    log.info(
        "dpd.compute | installments=%d | payments=%d → running %s mode",
        len(insts), len(pays), mode,
    )

    if mode == "cascade":
        results = list(cascade_fifo.compute_from_data(insts, pays, cfg))
    else:
        results = list(join_installment.compute_from_data(insts, pays, cfg))

    log.info(
        "dpd.compute | results=%d | in_arrears=%d",
        len(results), sum(1 for r in results if r.get("dpd_current", 0) > 0),
    )

    # Contratos del loan_tape sin resultado → dpd_current=0, amount_in_arrears=0
    contracts = loan_tape.select(pl.col(key)).rename({key: "borrower_contract_id"})

    if not results:
        return contracts.with_columns([
            pl.lit(0).alias("dpd_current"),
            pl.lit(0.0).alias("amount_in_arrears"),
        ]).rename({"borrower_contract_id": key})

    results_df = pl.DataFrame(results).with_columns(
        pl.col("amount_in_arrears").cast(pl.Float64)
    )

    # Unir con SPI para obtener borrower_contract_id por installment id
    spi_ids = spi_df.select(["id", "borrower_contract_id"])
    results_df = results_df.join(spi_ids, on="id", how="left")

    # Agregar por contrato
    per_contract = (
        results_df
        .with_columns(
            pl.when(pl.col("dpd_current") > 0)
            .then(pl.col("amount_in_arrears"))
            .otherwise(0.0)
            .alias("_arrears_in_mora")
        )
        .group_by("borrower_contract_id")
        .agg([
            pl.col("dpd_current").max(),
            pl.col("_arrears_in_mora").sum().alias("amount_in_arrears"),
        ])
    )

    # Join contra contratos del loan_tape para rellenar los que no tienen cuotas
    out = (
        contracts
        .join(per_contract, on="borrower_contract_id", how="left")
        .with_columns([
            pl.col("dpd_current").fill_null(0).cast(pl.Int64),
            pl.col("amount_in_arrears").fill_null(0.0),
        ])
        .rename({"borrower_contract_id": key})
    )

    log.info("[END] dpd.compute | dpd_current_max=%d", out["dpd_current"].max() or 0)
    return out
