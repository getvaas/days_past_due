"""Lectura de fechas máximas (last_*) de payments_db para el mensaje de respuesta.

Solo lectura — no escribe nada a la BD. La lectura de las tablas de cálculo vive en
excel_runner.load_schedule / load_payment_tape.

Requiere acceso al host MySQL (credenciales resueltas por DBConfig.load()).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from .config import DBConfig
from .integrations.db import connect, cursor


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
