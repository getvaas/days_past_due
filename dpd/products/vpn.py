"""Product: Valor Presente Neto (VPN / NPV).

Calcula el VPN de cada contrato usando el schedule de cuotas futuras
descontado a la tasa de interés pasada en el mensaje.

Columna que añade:
    vpn — valor presente neto de los flujos futuros del contrato

Fórmula:
    VPN = Σ [ gross_amount_i / (1 + r)^t_i ]
    donde t_i = días desde hoy hasta el vencimiento de la cuota i, en años.

Notas:
    - Solo incluye cuotas con fecha futura (date > calc_date).
    - interest_rate es anual (ej. 0.15 = 15% anual).
    - Si interest_rate es None o 0, VPN = suma de cuotas futuras (sin descuento).
"""
from __future__ import annotations

from datetime import date

import pandas as pd


def compute(
    loan_tape: pd.DataFrame,
    spi_df: pd.DataFrame,
    key: str,
    interest_rate: float | None = None,
    calc_date: date | None = None,
) -> pd.DataFrame:
    """Calcula VPN por contrato y lo agrega al loan tape.

    Args:
        loan_tape:     DataFrame con una fila por contrato.
        spi_df:        DataFrame de scheduled_payments_installments con columnas
                       borrower_contract_id, date/installment_date, gross_amount.
        key:           Columna en loan_tape que identifica el contrato.
        interest_rate: Tasa de interés anual (ej. 0.15). Si es None → VPN sin descuento.
        calc_date:     Fecha base para el descuento. Default: hoy.

    Returns:
        loan_tape con columna `vpn` agregada.
    """
    if calc_date is None:
        calc_date = date.today()

    spi = spi_df.copy()

    # Normalizar nombre de columna de fecha
    if "installment_date" in spi.columns:
        spi["_date"] = pd.to_datetime(spi["installment_date"]).dt.date
    elif "date" in spi.columns:
        spi["_date"] = pd.to_datetime(spi["date"]).dt.date
    else:
        raise ValueError("spi_df debe tener columna 'date' o 'installment_date'")

    spi["gross_amount"] = pd.to_numeric(spi["gross_amount"], errors="coerce").fillna(0)

    # Solo cuotas futuras
    spi_future = spi[spi["_date"] > calc_date].copy()

    if spi_future.empty:
        out = loan_tape.copy()
        out["vpn"] = 0.0
        return out

    # Calcular factor de descuento por cuota
    r = interest_rate or 0.0

    def _discount_factor(due_date: date) -> float:
        days = (due_date - calc_date).days
        t_years = days / 365.25
        if r == 0:
            return 1.0
        return 1.0 / ((1 + r) ** t_years)

    spi_future = spi_future.copy()
    spi_future["_factor"] = spi_future["_date"].apply(_discount_factor)
    spi_future["_pv"] = spi_future["gross_amount"] * spi_future["_factor"]

    vpn_by_contract = (
        spi_future.groupby("borrower_contract_id", as_index=False)
                  .agg(vpn=("_pv", "sum"))
                  .rename(columns={"borrower_contract_id": key})
    )

    out = loan_tape.copy()
    out = out.merge(vpn_by_contract, on=key, how="left")
    out["vpn"] = out["vpn"].fillna(0.0).round(2)
    return out
