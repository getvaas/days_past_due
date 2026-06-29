"""Mode 2 — Cascada FIFO.

Para cada contrato, los pagos (ordenados por payment_date ASC) se acumulan en un
pool y se aplican a las cuotas (ordenadas por date ASC). El excedente de un pago
fluye a la siguiente cuota.

Orden de aplicación dentro de cada cuota:
    guarantee → principal → interest → moratory_interest → tax → fee
moratory_interest no existe del lado scheduled, así que ese bucket es 0 en el
componente de la cuota; sigue presente en el orden por consistencia con el spec.

Entry point: `compute_from_data(installments, payments, cfg)` — lógica pura sobre
listas de dicts, sin dependencia de MySQL. Los datos se cargan en la capa de
productos/loaders y se pasan ya como dicts.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable, Iterator

from ..config import RunConfig
from ..utils.decimals import to_decimal as _zero_to_dec

log = logging.getLogger(__name__)

# Buckets in spec order. moratory_interest is unknown on the schedule side → 0.
BUCKETS = (
    "guarantee_amount",
    "principal_amount",
    "interest_amount",
    "moratory_interest_amount",
    "tax_amount",
    "fee_amount",
)


def _apply_pool_to_installment(pool: Decimal, components: dict) -> tuple:
    """Drain the pool into the installment's buckets in spec order.

    Returns (pool_remaining, applied_total).
    """
    applied = Decimal(0)
    for bucket in BUCKETS:
        owed = components.get(bucket, Decimal(0))
        if owed <= 0 or pool <= 0:
            continue
        take = owed if pool >= owed else pool
        pool -= take
        applied += take
    return pool, applied


def _dpd(installment_date: date, calc_date: date, grace_days: int = 1) -> int:
    return max((calc_date - installment_date).days - grace_days, 0)


def compute_from_data(
    installments: Iterable[dict],
    payments: Iterable[dict],
    cfg: RunConfig,
) -> Iterator[dict]:
    """Lógica pura sin BD.

    installments: dicts con id, borrower_contract_id, installment_date, gross_amount,
                  guarantee_amount, principal_amount, interest_amount, tax_amount,
                  fee_amount.
    payments: dicts con borrower_contract_id, payment_date, total_payment.

    El orden cascada FIFO asume cuotas ordenadas por (date asc, id asc) y pagos
    por (payment_date asc, id asc) dentro de cada contrato. Re-ordeno acá por
    seguridad — el SQL ya viene con ese orden, pero datos sintéticos no.
    """
    installments = list(installments)
    payments = list(payments)

    by_contract_inst: dict = defaultdict(list)
    for row in installments:
        by_contract_inst[row["borrower_contract_id"]].append(row)
    for k in by_contract_inst:
        by_contract_inst[k].sort(key=lambda r: (r["installment_date"], r.get("id") or 0))

    by_contract_pay: dict = defaultdict(list)
    for row in payments:
        if row.get("payment_date") is None:
            continue
        by_contract_pay[row["borrower_contract_id"]].append(row)
    for k in by_contract_pay:
        by_contract_pay[k].sort(key=lambda r: (r["payment_date"], r.get("id") or 0))

    log.info(
        "cascade mode: %d contracts, %d installments, %d payments",
        len(by_contract_inst), len(installments), len(payments),
    )

    for contract_id, inst_rows in by_contract_inst.items():
        # Pool of available payment money for this contract.
        pool = sum(
            (_zero_to_dec(p["total_payment"]) for p in by_contract_pay.get(contract_id, [])),
            Decimal(0),
        )

        for inst in inst_rows:
            gross = _zero_to_dec(inst["gross_amount"])
            components = {
                "guarantee_amount": _zero_to_dec(inst["guarantee_amount"]),
                "principal_amount": _zero_to_dec(inst["principal_amount"]),
                "interest_amount": _zero_to_dec(inst["interest_amount"]),
                "moratory_interest_amount": Decimal(0),
                "tax_amount": _zero_to_dec(inst["tax_amount"]),
                "fee_amount": _zero_to_dec(inst["fee_amount"]),
            }

            pool, applied = _apply_pool_to_installment(pool, components)

            threshold = Decimal(str(getattr(cfg, "paid_threshold", 1.0)))
            if cfg.partial_payment_counts:
                paid = applied > 0
            else:
                paid = applied >= gross * threshold

            if paid:
                dpd_current = 0
                arrears = Decimal(0)
            else:
                dpd_current = _dpd(inst["installment_date"], cfg.calculation_date, cfg.grace_days)
                arrears = gross - applied
                if arrears < 0:
                    arrears = Decimal(0)

            yield {
                "id": inst["id"],
                "dpd_current": dpd_current,
                "amount_in_arrears": arrears,
            }
