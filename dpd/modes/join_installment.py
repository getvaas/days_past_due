"""Mode 1 — Join scheduled_payments_installments to payment_tape by installment ref.

Pagos agregados con SUM(total_payment) y comparados contra gross_amount.

Entry point: `compute_from_data(installments, payments, cfg)` — lógica pura sobre
listas de dicts, sin dependencia de MySQL. Los datos se cargan en la capa de
productos/loaders y se pasan ya como dicts.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable, Iterator

from ..config import RunConfig
from ..utils.decimals import to_decimal as _to_dec

log = logging.getLogger(__name__)


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
    installments = list(installments)
    paid_by = aggregate_payments_by_ref(payments)
    log.info(
        "join mode: installments=%d | payment_refs=%d → processing",
        len(installments), len(paid_by),
    )
    for inst in installments:
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
