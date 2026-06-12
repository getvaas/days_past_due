"""Mode 1 — Join scheduled_payments_installments to payment_tape by installment ref.

Pagos agregados con SUM(total_payment) y comparados contra gross_amount.
Compatible con MySQL 5.7+ (sin CTEs).

Dos puntos de entrada:
- `compute(conn, cfg)`: trae los datos via SQL y produce DPD por cuota.
- `compute_from_data(installments, payments, cfg)`: misma lógica pura sobre listas
  de dicts. Usado por tests/notebook para no depender de MySQL.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable, Iterator

from ..config import RunConfig

log = logging.getLogger(__name__)

# LEFT JOIN para no perder cuotas sin pago. La subquery agrega payment_tape
# por (borrower_contract_id, borrower_installment_reference).
#
# Nota: cada lado se filtra por su propia columna de company (payment_tape.company_id
# numérico vs scheduled_payments_installments.company_code string), así que NO se
# joinean por company — sí por contrato + referencia de cuota.
SELECT_SQL = """
SELECT
    spi.id                                  AS id,
    spi.borrower_contract_id                AS borrower_contract_id,
    spi.borrower_installment_reference      AS borrower_installment_reference,
    spi.`date`                              AS installment_date,
    spi.gross_amount                        AS gross_amount,
    COALESCE(p.total_paid, 0)               AS total_paid
FROM scheduled_payments_installments spi
LEFT JOIN (
    SELECT borrower_contract_id,
           borrower_installment_reference,
           SUM(total_payment) AS total_paid
    FROM payment_tape
    WHERE company_id = %(company_id)s
      AND borrower_installment_reference IS NOT NULL
    GROUP BY borrower_contract_id, borrower_installment_reference
) p
  ON p.borrower_contract_id = spi.borrower_contract_id
 AND p.borrower_installment_reference = spi.borrower_installment_reference
WHERE spi.company_code = %(company_code)s;
"""


def _to_dec(v) -> Decimal:
    if v is None:
        return Decimal(0)
    # pandas representa celdas vacías como float('nan'); tratarlas como 0.
    if isinstance(v, float) and v != v:
        return Decimal(0)
    # str() para evitar imprecisión al convertir floats que vengan de pandas/Excel.
    return Decimal(str(v))


def _dpd_for_row(
    installment_date: date,
    gross_amount: Decimal,
    total_paid: Decimal,
    cfg: RunConfig,
) -> tuple:
    threshold = Decimal(str(getattr(cfg, "paid_threshold", 1.0)))
    paid = total_paid >= gross_amount * threshold
    if paid:
        return 0, Decimal(0)
    days_late = (cfg.calculation_date - installment_date).days - cfg.grace_days
    dpd = max(days_late, 0)
    arrears = gross_amount - total_paid
    if arrears < 0:
        arrears = Decimal(0)
    return dpd, arrears


def aggregate_payments_by_ref(payments: Iterable[dict]) -> dict:
    """Suma total_payment por (borrower_contract_id, borrower_installment_reference).

    Ignora pagos con installment_reference vacío/None — el join SQL hace lo mismo.
    """
    sums: dict = {}
    for p in payments:
        ref = p.get("borrower_installment_reference")
        if ref is None or (isinstance(ref, str) and not ref.strip()):
            continue
        key = (p["borrower_contract_id"], str(ref))
        sums[key] = sums.get(key, Decimal(0)) + _to_dec(p.get("total_payment"))
    return sums


def compute_from_data(
    installments: Iterable[dict],
    payments: Iterable[dict],
    cfg: RunConfig,
) -> Iterator[dict]:
    """Lógica pura sin BD.

    installments: dicts con id, borrower_contract_id, borrower_installment_reference,
                  installment_date, gross_amount.
    payments: dicts con borrower_contract_id, borrower_installment_reference, total_payment.
    """
    paid_by = aggregate_payments_by_ref(payments)
    count = 0
    for inst in installments:
        count += 1
        key = (inst["borrower_contract_id"], str(inst["borrower_installment_reference"]))
        total_paid = paid_by.get(key, Decimal(0))
        gross = _to_dec(inst.get("gross_amount"))
        dpd, arrears = _dpd_for_row(
            installment_date=inst["installment_date"],
            gross_amount=gross,
            total_paid=total_paid,
            cfg=cfg,
        )
        yield {
            "id": inst["id"],
            "dpd_current": dpd,
            "amount_in_arrears": arrears,
        }
    log.info("join mode: %d installments processed", count)


def compute(conn, cfg: RunConfig) -> Iterator[dict]:
    """Yield {id, dpd_current, amount_in_arrears} por cuota — desde la BD."""
    from ..integrations.db import cursor
    with cursor(conn) as cur:
        cur.execute(
            SELECT_SQL,
            {"company_id": cfg.company_id, "company_code": cfg.company_code},
        )
        rows = cur.fetchall()

    log.info(
        "join mode: %d installments fetched for company_code=%s / company_id=%s",
        len(rows), cfg.company_code, cfg.company_id,
    )

    # Ya viene pre-agregado por el SQL; emulamos la forma esperada por _dpd_for_row directamente.
    for row in rows:
        gross = _to_dec(row.get("gross_amount"))
        paid = _to_dec(row.get("total_paid"))
        dpd, arrears = _dpd_for_row(
            installment_date=row["installment_date"],
            gross_amount=gross,
            total_paid=paid,
            cfg=cfg,
        )
        yield {
            "id": row["id"],
            "dpd_current": dpd,
            "amount_in_arrears": arrears,
        }
