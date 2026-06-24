"""Product: Valor Presente Neto (VPN / NPV).

Columna que devuelve:
    vpn — valor presente neto de los flujos futuros del contrato

Fórmula:
    VPN = Σ [ gross_amount_i / (1 + r)^t_i ]
    donde t_i = días desde calc_date hasta el vencimiento de la cuota i, en años.
"""
from __future__ import annotations

from datetime import date

import polars as pl


def compute(
    loan_tape: pl.DataFrame,
    spi_df: pl.DataFrame,
    key: str,
    interest_rate: float | None = None,
    calc_date: date | None = None,
) -> pl.DataFrame:
    """Calcula VPN por contrato.

    Devuelve un DataFrame con solo (key, vpn) —
    sin copiar el loan_tape. El join al loan_tape lo hace el caller.
    """
    if calc_date is None:
        calc_date = date.today()

    contracts = loan_tape.select(pl.col(key))

    date_col = "installment_date" if "installment_date" in spi_df.columns else "date"
    spi = (
        spi_df
        .with_columns(pl.col(date_col).cast(pl.Date).alias("_date"))
        .with_columns(pl.col("gross_amount").cast(pl.Float64, strict=False).fill_null(0.0))
        .filter(pl.col("_date") > pl.lit(calc_date))
    )

    if spi.is_empty():
        return contracts.with_columns(pl.lit(0.0).alias("vpn"))

    r = interest_rate or 0.0

    spi = spi.with_columns(
        ((pl.col("_date") - pl.lit(calc_date)).dt.total_days() / 365.25).alias("_t_years")
    )

    if r == 0.0:
        spi = spi.with_columns(pl.lit(1.0).alias("_factor"))
    else:
        spi = spi.with_columns(
            (1.0 / (1.0 + r) ** pl.col("_t_years")).alias("_factor")
        )

    vpn_by_contract = (
        spi
        .with_columns((pl.col("gross_amount") * pl.col("_factor")).alias("_pv"))
        .group_by("borrower_contract_id")
        .agg(pl.col("_pv").sum().round(2).alias("vpn"))
        .rename({"borrower_contract_id": key})
    )

    return (
        contracts
        .join(vpn_by_contract, on=key, how="left")
        .with_columns(pl.col("vpn").fill_null(0.0))
    )
