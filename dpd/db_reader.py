"""Lectura de scheduled_payments_installments y payment_tape desde MySQL.

Solo lectura — no escribe nada a la BD.

Requiere acceso VPC al host MySQL. Configura las variables de entorno:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from .config import DBConfig
from .integrations.db import connect, cursor


SPI_SQL = """
SELECT
    id,
    company_code,
    borrower_contract_id,
    borrower_installment_reference,
    `date`            AS installment_date,
    gross_amount,
    COALESCE(guarantee_amount, 0) AS guarantee_amount,
    COALESCE(principal_amount, 0) AS principal_amount,
    COALESCE(interest_amount, 0)  AS interest_amount,
    COALESCE(tax_amount, 0)       AS tax_amount,
    COALESCE(fee_amount, 0)       AS fee_amount
FROM scheduled_payments_installments
WHERE company_code = %(company_code)s
ORDER BY borrower_contract_id, `date` ASC, id ASC;
"""

PAYMENTS_SQL = """
SELECT
    borrower_contract_id,
    borrower_installment_reference,
    payment_date,
    total_payment,
    MAX(payment_date) OVER (PARTITION BY company_id) AS last_payment_date
FROM payment_tape
WHERE company_id = %(company_id)s
  AND payment_date IS NOT NULL
  AND total_payment > 0
ORDER BY borrower_contract_id, payment_date ASC, id ASC;
"""

SPI_LAST_DATE_SQL = """
SELECT MAX(`date`) AS last_schedule_payment_date
FROM scheduled_payments_installments
WHERE company_code = %(company_code)s;
"""

PAYMENTS_LAST_DATE_SQL = """
SELECT MAX(payment_date) AS last_payment_tape_date
FROM payment_tape
WHERE company_id = %(company_id)s;
"""

PAYMENTS_LAST_PAYMENT_SQL = """
SELECT MAX(payment_date) AS last_payment_date
FROM payment_tape
WHERE company_id = %(company_id)s
  AND total_payment > 0;
"""


def read_schedule(company_code: str | int, db_cfg: Optional[DBConfig] = None) -> pd.DataFrame:
    """Lee todas las cuotas de scheduled_payments_installments para una company."""
    cfg = db_cfg or DBConfig.load()
    conn = connect(cfg)
    try:
        with cursor(conn) as cur:
            cur.execute(SPI_SQL, {"company_code": str(company_code)})
            rows = cur.fetchall()
    finally:
        conn.close()

    df = pd.DataFrame(rows)
    if not df.empty:
        df["installment_date"] = pd.to_datetime(df["installment_date"]).dt.date
    return df


def read_payments(company_id: int, db_cfg: Optional[DBConfig] = None) -> pd.DataFrame:
    """Lee todos los pagos de payment_tape para una company."""
    cfg = db_cfg or DBConfig.load()
    conn = connect(cfg)
    try:
        with cursor(conn) as cur:
            cur.execute(PAYMENTS_SQL, {"company_id": company_id})
            rows = cur.fetchall()
    finally:
        conn.close()

    df = pd.DataFrame(rows)
    if not df.empty:
        df["payment_date"] = pd.to_datetime(df["payment_date"]).dt.date
    return df


def read_last_dates(
    company_code: str | int,
    company_id: int,
    db_cfg: Optional[DBConfig] = None,
) -> dict[str, Optional[date]]:
    """Devuelve las fechas más recientes de cada fuente de datos.

    Usado para poblar metadata.last_* en el mensaje de respuesta.
    """
    cfg = db_cfg or DBConfig.load()
    conn = connect(cfg)
    try:
        with cursor(conn) as cur:
            cur.execute(SPI_LAST_DATE_SQL, {"company_code": str(company_code)})
            spi_row = cur.fetchone()

            cur.execute(PAYMENTS_LAST_DATE_SQL, {"company_id": company_id})
            pt_row = cur.fetchone()

            cur.execute(PAYMENTS_LAST_PAYMENT_SQL, {"company_id": company_id})
            pay_row = cur.fetchone()
    finally:
        conn.close()

    def _to_date(v) -> Optional[date]:
        if v is None:
            return None
        if isinstance(v, date):
            return v
        return pd.Timestamp(v).date()

    return {
        "last_schedule_payment_date": _to_date(spi_row["last_schedule_payment_date"] if spi_row else None),
        "last_payment_tape_date": _to_date(pt_row["last_payment_tape_date"] if pt_row else None),
        "last_payment_date": _to_date(pay_row["last_payment_date"] if pay_row else None),
    }
