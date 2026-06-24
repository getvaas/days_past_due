"""Product: Total Amount.

Columna que devuelve:
    total_amount_paid — suma de todos los pagos en payment_tape para el contrato
"""
from __future__ import annotations

import polars as pl


def compute(
    loan_tape: pl.DataFrame,
    payments_df: pl.DataFrame,
    key: str,
) -> pl.DataFrame:
    """Suma total_payment por contrato.

    Devuelve un DataFrame con solo (key, total_amount_paid) —
    sin copiar el loan_tape. El join al loan_tape lo hace el caller.
    """
    contracts = loan_tape.select(pl.col(key))

    if payments_df.is_empty():
        return contracts.with_columns(pl.lit(0.0).alias("total_amount_paid"))

    total_by_contract = (
        payments_df
        .with_columns(pl.col("total_payment").cast(pl.Float64, strict=False))
        .filter(pl.col("total_payment") > 0)
        .group_by("borrower_contract_id")
        .agg(pl.col("total_payment").sum().alias("total_amount_paid"))
        .rename({"borrower_contract_id": key})
    )

    return (
        contracts
        .join(total_by_contract, on=key, how="left")
        .with_columns(pl.col("total_amount_paid").fill_null(0.0))
    )
