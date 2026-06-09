"""Product: Total Amount.

Agrega al loan tape la suma total de pagos recibidos por contrato.
Columna que añade:
    total_amount_paid — suma de todos los pagos en payment_tape para el contrato
"""
from __future__ import annotations

import pandas as pd


def compute(
    loan_tape: pd.DataFrame,
    payments_df: pd.DataFrame,
    key: str,
) -> pd.DataFrame:
    """Suma total_payment por contrato y lo agrega al loan tape.

    Args:
        loan_tape:    DataFrame con una fila por contrato.
        payments_df:  DataFrame de payment_tape con columnas
                      borrower_contract_id y total_payment.
        key:          Columna en loan_tape que identifica el contrato
                      (debe coincidir con borrower_contract_id en payments).

    Returns:
        loan_tape con columna `total_amount_paid` agregada.
    """
    if payments_df.empty:
        out = loan_tape.copy()
        out["total_amount_paid"] = 0.0
        return out

    pay = payments_df.copy()
    pay["total_payment"] = pd.to_numeric(pay["total_payment"], errors="coerce").fillna(0)

    # Filtrar pagos válidos
    pay = pay[pay["total_payment"] > 0]

    total_by_contract = (
        pay.groupby("borrower_contract_id", as_index=False)
           .agg(total_amount_paid=("total_payment", "sum"))
           .rename(columns={"borrower_contract_id": key})
    )

    out = loan_tape.copy()
    out = out.merge(total_by_contract, on=key, how="left")
    out["total_amount_paid"] = out["total_amount_paid"].fillna(0.0)
    return out
