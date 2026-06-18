"""Read-only summary queries por contrato. No escriben nada en la BD."""
from __future__ import annotations

from .db import cursor

CURRENT_DPD_BY_CONTRACT = """
SELECT borrower_contract_id,
       MAX(dpd_current) AS dpd_credito
FROM scheduled_payments_installments
WHERE company_id = %(company_id)s
GROUP BY borrower_contract_id
ORDER BY dpd_credito DESC, borrower_contract_id;
"""

MAX_DPD_BY_CONTRACT = """
SELECT borrower_contract_id,
       MAX(dpd_max) AS max_tiempo_mora
FROM scheduled_payments_installments
WHERE company_id = %(company_id)s
GROUP BY borrower_contract_id
ORDER BY max_tiempo_mora DESC, borrower_contract_id;
"""


def current_dpd_by_contract(conn, company_id: int) -> list[dict]:
    with cursor(conn) as cur:
        cur.execute(CURRENT_DPD_BY_CONTRACT, {"company_id": company_id})
        return list(cur.fetchall())


def max_dpd_by_contract(conn, company_id: int) -> list[dict]:
    with cursor(conn) as cur:
        cur.execute(MAX_DPD_BY_CONTRACT, {"company_id": company_id})
        return list(cur.fetchall())
