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
        loan_tape["total_amount_paid"] = 0.0
        return loan_tape

    amt = pd.to_numeric(payments_df["total_payment"], errors="coerce")
    mask = amt > 0  # NaN > 0 es False, así que filtra inválidos y no positivos

    total_by_contract = (
        payments_df.loc[mask, ["borrower_contract_id"]]
        .assign(amt=amt[mask])
        .groupby("borrower_contract_id", as_index=False, sort=False)["amt"]
        .sum()
        .rename(columns={"borrower_contract_id": key, "amt": "total_amount_paid"})
    )

    loan_tape = loan_tape.merge(total_by_contract, on=key, how="left")
    loan_tape["total_amount_paid"] = loan_tape["total_amount_paid"].fillna(0.0)
    return loan_tape
