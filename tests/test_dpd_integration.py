"""Tests de integración DPD — docs/uses-cases/cases.md

Mismos 18 escenarios que test_dpd_use_cases.py pero con MySQL real:
    INSERT en payments_db_test → load_schedule / load_payment_tape → dpd_product.compute()

Requiere el contenedor vaas_local_mysql corriendo:
    cd ~/Desktop/wks/local-infra && docker compose up -d

Correr solo estos tests:
    pytest tests/test_dpd_integration.py -v
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from dpd.excel_runner import load_payment_tape, load_schedule
from dpd.products import dpd as dpd_product

# ─── Constantes ──────────────────────────────────────────────────────────────

CALC_DATE = date(2026, 10, 3)
KEY = "borrower_contract_id"

JUN = date(2026, 6, 1)
JUL = date(2026, 7, 1)
AUG = date(2026, 8, 1)
SEP = date(2026, 9, 1)
OCT = date(2026, 10, 1)

DPD_JUN = (CALC_DATE - JUN).days - 1   # 123
DPD_JUL = (CALC_DATE - JUL).days - 1   # 93
DPD_AUG = (CALC_DATE - AUG).days - 1   # 62
DPD_SEP = (CALC_DATE - SEP).days - 1   # 31
DPD_OCT = (CALC_DATE - OCT).days - 1   # 1

AMOUNT = Decimal("1000.00")


# ─── Helper de cómputo ───────────────────────────────────────────────────────

def _compute(company_id: int, db_cfg, mode: str,
             paid_threshold: float = 1.0,
             previous_output=None):
    """Carga datos desde payments_db_test y corre dpd_product.compute()."""
    spi_df = load_schedule(company_id, db_cfg=db_cfg)
    pay_df = load_payment_tape(company_id, db_cfg=db_cfg)

    assert not spi_df.empty, (
        f"company_id={company_id}: load_schedule no devolvió filas — "
        "verificá que insert.installment() fue llamado antes de _compute()"
    )
    print(
        f"\n  [DB] company_id={company_id} | "
        f"cuotas={len(spi_df)} | pagos={len(pay_df)} | mode={mode}"
    )

    contracts = spi_df["borrower_contract_id"].unique().tolist()
    loan_tape = pd.DataFrame([{KEY: c} for c in contracts])

    result = dpd_product.compute(
        loan_tape=loan_tape,
        spi_df=spi_df,
        payments_df=pay_df,
        key=KEY,
        calc_date=CALC_DATE,
        mode=mode,
        paid_threshold=paid_threshold,
        previous_output=previous_output,
    )
    return result.iloc[0]


# ─── Caso 1 — Happy path ─────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso1_happy_path(insert, db_cfg, mode):
    cid, company_id = "C01", 1
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 2 — Pago parcial en la última cuota ────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso2_pago_parcial_ultima_cuota(insert, db_cfg, mode):
    cid, company_id = "C02", 2
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)
    insert.installment(company_id, cid, "REF-5", OCT)
    insert.payment(company_id, cid, "REF-5", OCT, Decimal("500.00"))

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == DPD_OCT
    assert row["amount_in_arrears"] == Decimal("500.00")


# ─── Caso 3 — Sin pagos registrados ──────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso3_sin_pagos(insert, db_cfg, mode):
    cid, company_id = "C03", 3
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == DPD_JUN
    assert row["amount_in_arrears"] == Decimal("4000.00")


# ─── Caso 4 — Pago atrasado ya regularizado ──────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso4_pago_atrasado_ya_regularizado(insert, db_cfg, mode):
    cid, company_id = "C04", 4
    dates = [JUN, JUL, AUG, SEP, OCT]
    payment_dates = [JUN, JUL, date(2026, 8, 16), SEP, OCT]  # ago: 15 días tarde
    for i, (due, pdate) in enumerate(zip(dates, payment_dates), 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", pdate, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso4_dpd_max_historico_preservado(insert, db_cfg, mode):
    cid, company_id = "C04B", 40
    dates = [JUN, JUL, AUG, SEP, OCT]
    payment_dates = [JUN, JUL, date(2026, 8, 16), SEP, OCT]
    for i, (due, pdate) in enumerate(zip(dates, payment_dates), 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", pdate, AMOUNT)

    previous_output = pd.DataFrame([{KEY: cid, "dpd_max": 15}])
    row = _compute(company_id, db_cfg, mode, previous_output=previous_output)
    assert row["dpd_current"] == 0
    assert row["dpd_max"] == 15


# ─── Caso 5 — Pago parcial en cuota intermedia ───────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_OCT, Decimal("500.00")),
    ("join",    DPD_AUG, Decimal("500.00")),
])
def test_caso5_pago_parcial_cuota_intermedia(insert, db_cfg, mode, exp_dpd, exp_arrears):
    cid, company_id = "C05", 5
    amounts = [AMOUNT, AMOUNT, Decimal("500.00"), AMOUNT, AMOUNT]
    for i, (due, amt) in enumerate(zip([JUN, JUL, AUG, SEP, OCT], amounts), 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, amt)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 6 — Pago anticipado ────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso6_pago_anticipado(insert, db_cfg, mode):
    cid, company_id = "C06", 6
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
    insert.payment(company_id, cid, "REF-1", JUN, AMOUNT)
    insert.payment(company_id, cid, "REF-2", JUN, AMOUNT)
    insert.payment(company_id, cid, "REF-3", JUN, AMOUNT)
    insert.payment(company_id, cid, "REF-4", SEP, AMOUNT)
    insert.payment(company_id, cid, "REF-5", OCT, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 7 — Sobrepago en una cuota ─────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso7_sobrepago_ultima_cuota(insert, db_cfg, mode):
    cid, company_id = "C07", 7
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)
    insert.installment(company_id, cid, "REF-5", OCT)
    insert.payment(company_id, cid, "REF-5", OCT, Decimal("1500.00"))

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 8 — Múltiples cuotas con pago parcial ──────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_SEP, Decimal("1500.00")),
    ("join",    DPD_AUG, Decimal("1500.00")),
])
def test_caso8_multiples_pagos_parciales(insert, db_cfg, mode, exp_dpd, exp_arrears):
    cid, company_id = "C08", 8
    amounts = [AMOUNT, AMOUNT, Decimal("500.00"), Decimal("500.00"), Decimal("500.00")]
    for i, (due, amt) in enumerate(zip([JUN, JUL, AUG, SEP, OCT], amounts), 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, amt)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 9 — Excedente de Sep cubre parcialmente Oct ────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_OCT, Decimal("500.00")),
    ("join",    DPD_OCT, Decimal("1000.00")),
])
def test_caso9_excedente_sep_cubre_oct(insert, db_cfg, mode, exp_dpd, exp_arrears):
    cid, company_id = "C09", 9
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
    insert.payment(company_id, cid, "REF-1", JUN, AMOUNT)
    insert.payment(company_id, cid, "REF-2", JUL, AMOUNT)
    insert.payment(company_id, cid, "REF-3", AUG, AMOUNT)
    insert.payment(company_id, cid, "REF-4", SEP, Decimal("1500.00"))

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 10 — Cuota pagada en dos partes ────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso10_cuota_en_dos_partes(insert, db_cfg, mode):
    cid, company_id = "C10", 10
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)
    insert.installment(company_id, cid, "REF-5", OCT)
    insert.payment(company_id, cid, "REF-5", OCT,               Decimal("500.00"))
    insert.payment(company_id, cid, "REF-5", date(2026, 10, 2), Decimal("500.00"))

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 11 — Mora prolongada con pago parcial reciente ─────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso11_mora_prolongada_pago_reciente(insert, db_cfg, mode):
    cid, company_id = "C11", 11
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
    insert.payment(company_id, cid, "REF-1", SEP, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == DPD_JUL
    assert row["amount_in_arrears"] == Decimal("4000.00")


# ─── Caso 12 — Pago el mismo día del corte ───────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso12_pago_mismo_dia_corte(insert, db_cfg, mode):
    cid, company_id = "C12", 12
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)
    insert.installment(company_id, cid, "REF-5", OCT)
    insert.payment(company_id, cid, "REF-5", CALC_DATE, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 13 — Diferencia de centavos por redondeo ───────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode,paid_threshold,exp_dpd,exp_arrears", [
    ("cascade", 1.0,  DPD_OCT, Decimal("0.50")),
    ("join",    1.0,  DPD_OCT, Decimal("0.50")),
    ("cascade", 0.95, 0,       Decimal("0")),
    ("join",    0.95, 0,       Decimal("0")),
])
def test_caso13_diferencia_centavos(insert, db_cfg, mode, paid_threshold, exp_dpd, exp_arrears):
    cid, company_id = "C13", 13
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)
    insert.installment(company_id, cid, "REF-5", OCT)
    insert.payment(company_id, cid, "REF-5", OCT, Decimal("999.50"))

    row = _compute(company_id, db_cfg, mode, paid_threshold=paid_threshold)
    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 14 — Crédito reestructurado ────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso14_credito_reestructurado(insert, db_cfg, mode):
    cid, company_id = "C14", 14
    new_amount = Decimal("800.00")
    insert.installment(company_id, cid, "REF-1", JUN)
    insert.installment(company_id, cid, "REF-2", JUL)
    insert.installment(company_id, cid, "REF-3", SEP, gross=new_amount)
    insert.installment(company_id, cid, "REF-4", OCT, gross=new_amount)
    insert.payment(company_id, cid, "REF-1", JUN, AMOUNT)
    insert.payment(company_id, cid, "REF-2", JUL, AMOUNT)
    insert.payment(company_id, cid, "REF-3", SEP, new_amount)
    insert.payment(company_id, cid, "REF-4", OCT, new_amount)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 15 — Pago duplicado ────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso15_pago_duplicado(insert, db_cfg, mode):
    cid, company_id = "C15", 15
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)
    insert.payment(company_id, cid, "REF-3", AUG, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 16 — Primera cuota nunca pagada ────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_OCT, Decimal("1000.00")),
    ("join",    DPD_JUN, Decimal("1000.00")),
])
def test_caso16_primera_cuota_nunca_pagada(insert, db_cfg, mode, exp_dpd, exp_arrears):
    cid, company_id = "C16", 16
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
    for i, due in enumerate([JUL, AUG, SEP, OCT], 2):
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 17 — Sin payment tape ──────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso17_sin_payment_tape(insert, db_cfg, mode):
    cid, company_id = "C17", 17
    for i, due in enumerate([JUN, JUL, AUG, SEP], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == DPD_JUN
    assert row["amount_in_arrears"] == Decimal("4000.00")


# ─── Caso 18 — Pagos normales y luego abandono ───────────────────────────────

@pytest.mark.integration
@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso18_abandono_desde_sep(insert, db_cfg, mode):
    cid, company_id = "C18", 18
    for i, due in enumerate([JUN, JUL, AUG, SEP, OCT], 1):
        insert.installment(company_id, cid, f"REF-{i}", due)
    for i, due in enumerate([JUN, JUL, AUG], 1):
        insert.payment(company_id, cid, f"REF-{i}", due, AMOUNT)

    row = _compute(company_id, db_cfg, mode)
    assert row["dpd_current"] == DPD_SEP
    assert row["amount_in_arrears"] == Decimal("2000.00")
