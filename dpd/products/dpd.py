"""Product: Days Past Due.

Agrega columnas DPD al loan tape por contrato.
Columnas que añade:
    dpd_current       — máximo DPD entre cuotas vencidas del contrato
    dpd_max           — high-watermark histórico: max(dpd_max_previo, dpd_current)
    amount_in_arrears — suma de arrears en cuotas con dpd > 0
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from ..config import RunConfig
from ..modes import cascade_fifo
from ..excel_runner import sanitize_schedule, sanitize_payment_tape, _installments_from_df, _payments_from_df


def compute(
    loan_tape: pd.DataFrame,
    spi_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    key: str,
    calc_date: date | None = None,
    grace_days: int = 1,
    mode: str = "cascade",
    paid_threshold: float = 1.0,
    previous_output: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Calcula DPD por contrato y lo agrega al loan tape.

    Args:
        loan_tape:        DataFrame con una fila por contrato. Debe tener la columna `key`.
        spi_df:           DataFrame de scheduled_payments_installments (desde DB o Excel).
        payments_df:      DataFrame de payment_tape (desde DB o Excel).
        key:              Nombre de la columna en loan_tape que identifica el contrato.
                          Debe coincidir con `borrower_contract_id` en spi y payments.
        calc_date:        Fecha de corte. Default: hoy.
        grace_days:       Días calendario de gracia. Default: 1.
        mode:             "cascade" (default) | "join".
        paid_threshold:   Fracción mínima pagada para considerar cuota al día (default 1.0 = 100%).
        previous_output:  Output del run anterior (leído desde S3) para recuperar dpd_max.
                          Si es None, dpd_max = dpd_current (primer run o sin historial).

    Returns:
        loan_tape con columnas `dpd_current`, `dpd_max` y `amount_in_arrears` agregadas.
    """
    if calc_date is None:
        calc_date = date.today()

    # Sanitizar inputs si vienen crudos
    spi_clean = sanitize_schedule(spi_df) if "installment_date" not in spi_df.columns else spi_df
    pay_clean = sanitize_payment_tape(payments_df) if "payment_date" not in payments_df.columns else payments_df

    # Renombrar columna `date` → `installment_date` si viene de la BD
    if "installment_date" not in spi_clean.columns and "date" in spi_clean.columns:
        spi_clean = spi_clean.rename(columns={"date": "installment_date"})

    spi_aligned = spi_clean.copy()
    pay_aligned = pay_clean.copy()

    cfg = RunConfig(
        company_id=0,
        company_code="*",
        mode=mode,
        partial_payment_counts=False,
        calculation_date=calc_date,
        grace_days=grace_days,
        paid_threshold=paid_threshold,
    )

    insts = _installments_from_df(spi_aligned)
    pays = _payments_from_df(pay_aligned)

    if mode == "cascade":
        results = list(cascade_fifo.compute_from_data(insts, pays, cfg))
    else:
        from ..modes import join_installment
        results = list(join_installment.compute_from_data(insts, pays, cfg))

    if not results:
        loan_tape = loan_tape.copy()
        loan_tape["dpd_current"] = 0
        loan_tape["dpd_max"] = 0
        loan_tape["amount_in_arrears"] = 0.0
        return loan_tape

    results_df = pd.DataFrame(results)
    results_df["amount_in_arrears"] = results_df["amount_in_arrears"].astype(float)

    # Unir con SPI para obtener el borrower_contract_id por installment id
    spi_ids = spi_aligned[["id", "borrower_contract_id"]].copy()
    results_df = results_df.merge(spi_ids, on="id", how="left")

    # Agregar por contrato: max DPD, suma arrears solo en cuotas en mora
    per_contract = (
        results_df.groupby("borrower_contract_id", as_index=False)
                  .agg(
                      dpd_current=("dpd_current", "max"),
                      amount_in_arrears=(
                          "amount_in_arrears",
                          lambda s: s[results_df.loc[s.index, "dpd_current"] > 0].sum(),
                      ),
                  )
    )

    # Merge contra el loan tape usando el key
    out = loan_tape.copy()
    out = out.merge(
        per_contract.rename(columns={"borrower_contract_id": key}),
        on=key,
        how="left",
    )
    out["dpd_current"] = out["dpd_current"].fillna(0).astype(int)
    out["amount_in_arrears"] = out["amount_in_arrears"].fillna(0.0)

    # dpd_max: high-watermark histórico.
    # Si hay output previo con dpd_max, tomamos max(prev, current). Si no, dpd_max = dpd_current.
    if previous_output is not None and "dpd_max" in previous_output.columns and key in previous_output.columns:
        prev_max = previous_output[[key, "dpd_max"]].copy()
        prev_max["dpd_max"] = pd.to_numeric(prev_max["dpd_max"], errors="coerce").fillna(0).astype(int)
        out = out.merge(prev_max.rename(columns={"dpd_max": "_prev_dpd_max"}), on=key, how="left")
        out["_prev_dpd_max"] = out["_prev_dpd_max"].fillna(0).astype(int)
        out["dpd_max"] = out[["dpd_current", "_prev_dpd_max"]].max(axis=1)
        out = out.drop(columns=["_prev_dpd_max"])
    else:
        out["dpd_max"] = out["dpd_current"]

    return out
