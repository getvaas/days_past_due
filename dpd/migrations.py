"""Idempotent schema migrations for the DPD columns (MySQL).

`ADD COLUMN IF NOT EXISTS` solo está disponible en MySQL 8.0.29+. Para ser
portable a versiones anteriores consultamos INFORMATION_SCHEMA primero.
"""
from __future__ import annotations

import logging

from .db import cursor

log = logging.getLogger(__name__)

REQUIRED_COLUMNS: dict[str, str] = {
    "dpd_current": "INT NOT NULL DEFAULT 0",
    "dpd_max": "INT NOT NULL DEFAULT 0",
    "amount_in_arrears": "DECIMAL(18,4) NOT NULL DEFAULT 0",
}

EXISTING_COLS_SQL = """
SELECT LOWER(COLUMN_NAME) AS name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'scheduled_payments_installments';
"""


def ensure_dpd_columns(conn) -> None:
    with cursor(conn) as cur:
        cur.execute(EXISTING_COLS_SQL)
        existing = {row["name"] for row in cur.fetchall()}

        added: list[str] = []
        for col, ddl in REQUIRED_COLUMNS.items():
            if col.lower() in existing:
                continue
            cur.execute(
                f"ALTER TABLE scheduled_payments_installments ADD COLUMN {col} {ddl};"
            )
            added.append(col)

    conn.commit()
    if added:
        log.info("Columnas DPD agregadas: %s", ", ".join(added))
    else:
        log.info("Columnas DPD ya existían — no se modificó el esquema")
