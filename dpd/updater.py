"""Persist DPD results back to scheduled_payments_installments (MySQL).

Idempotente: dpd_current y amount_in_arrears se sobreescriben en cada corrida;
dpd_max se actualiza solo si el nuevo valor es mayor (high-watermark).
"""
from __future__ import annotations

import logging
from typing import Iterable

from .db import cursor

log = logging.getLogger(__name__)

UPDATE_CURRENT_SQL = """
UPDATE scheduled_payments_installments
SET dpd_current = %s,
    amount_in_arrears = %s,
    last_update_date = NOW()
WHERE id = %s;
"""

UPDATE_MAX_SQL = """
UPDATE scheduled_payments_installments
SET dpd_max = %s,
    last_update_date = NOW()
WHERE id = %s
  AND %s > dpd_max;
"""

BATCH_SIZE = 1000


def apply_results(conn, results: Iterable[dict]) -> int:
    """Write results in batches inside a single transaction. Returns rows updated."""
    total = 0
    batch: list = []

    with cursor(conn, dict_rows=False) as cur:
        for row in results:
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                _flush(cur, batch)
                total += len(batch)
                batch.clear()
        if batch:
            _flush(cur, batch)
            total += len(batch)

    conn.commit()
    log.info("updater: %d installments written", total)
    return total


def _flush(cur, batch: list) -> None:
    current_rows = [(r["dpd_current"], r["amount_in_arrears"], r["id"]) for r in batch]
    cur.executemany(UPDATE_CURRENT_SQL, current_rows)

    max_rows = [(r["dpd_current"], r["id"], r["dpd_current"]) for r in batch]
    cur.executemany(UPDATE_MAX_SQL, max_rows)
