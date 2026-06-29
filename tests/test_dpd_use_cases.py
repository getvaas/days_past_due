"""Tests de casos de uso DPD — docs/uses-cases/cases.md

18 escenarios × 2 modos (cascade, join).
Caso 13: además 2 variantes de paid_threshold (1.0 y 0.95).

calc_date  = 2026-10-03
Cuotas     = mensuales, día 1 de cada mes (Jun–Oct 2026)
grace_days = 1 (default del producto)

Punto de entrada: dpd_product.compute() — puro, sin BD ni S3.

DPDs al corte (grace_days=1):
    Jun 1 → 123  |  Jul 1 → 93  |  Aug 1 → 62  |  Sep 1 → 31  |  Oct 1 → 1

Diferencias cascade vs join:
    Caso  5: cascade dpd=1  / join dpd=62  (mismo arrears=$500)
    Caso  8: cascade dpd=31 / join dpd=62  (mismo arrears=$1500)
    Caso  9: cascade arrears=$500 / join arrears=$1000
    Caso 16: cascade dpd=1  / join dpd=123 (mismo arrears=$1000)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import polars as pl
import pytest

from dpd.products import dpd as dpd_product

# ─── Constantes globales ─────────────────────────────────────────────────────

CALC_DATE = date(2026, 10, 3)
KEY = "borrower_contract_id"

JUN = date(2026, 6, 1)
JUL = date(2026, 7, 1)
AUG = date(2026, 8, 1)
SEP = date(2026, 9, 1)
OCT = date(2026, 10, 1)

# DPD de cada fecha al 2026-10-03 con grace_days=1
DPD_JUN = (CALC_DATE - JUN).days - 1   # 123
DPD_JUL = (CALC_DATE - JUL).days - 1   # 93
DPD_AUG = (CALC_DATE - AUG).days - 1   # 62
DPD_SEP = (CALC_DATE - SEP).days - 1   # 31
DPD_OCT = (CALC_DATE - OCT).days - 1   # 1

AMOUNT = Decimal("1000.00")


# ─── Builders de fixtures ────────────────────────────────────────────────────

def inst(cid: str, iid: int, due: date, ref: str, gross: Decimal = AMOUNT) -> dict:
    """Cuota mínima compatible con _installments_from_pl (sin pasar por los loaders)."""
    return {
        "id": iid,
        "borrower_contract_id": cid,
        "installment_date": due,
        "borrower_installment_reference": ref,
        "gross_amount": gross,
        "principal_amount": gross,
        "interest_amount": Decimal("0"),
        "guarantee_amount": Decimal("0"),
        "tax_amount": Decimal("0"),
        "fee_amount": Decimal("0"),
    }


def pay(cid: str, pdate: date, amount: Decimal, ref: str | None = None) -> dict:
    """Pago compatible con _payments_from_df.

    ref debe coincidir con borrower_installment_reference de la cuota para que
    el modo join asocie el pago. En cascade el ref se ignora — solo cuenta el total.
    """
    return {
        "borrower_contract_id": cid,
        "payment_date": pdate,
        "total_payment": amount,
        "borrower_installment_reference": ref,
    }


def _run(
    installments: list[dict],
    payments: list[dict],
    cid: str,
    mode: str,
    paid_threshold: float = 1.0,
) -> dict:
    """Ejecuta dpd_product.compute() y devuelve la fila del contrato."""
    spi_df = pl.DataFrame(installments)
    pay_df = (
        pl.DataFrame(payments)
        if payments
        else pl.DataFrame(schema={
            "borrower_contract_id": pl.Utf8,
            "payment_date": pl.Date,
            "total_payment": pl.Float64,
            "borrower_installment_reference": pl.Utf8,
        })
    )
    loan_tape = pl.DataFrame([{KEY: cid}])
    result = dpd_product.compute(
        loan_tape=loan_tape,
        spi_df=spi_df,
        payments_df=pay_df,
        key=KEY,
        calc_date=CALC_DATE,
        mode=mode,
        paid_threshold=paid_threshold,
    )
    return result.row(0, named=True)


# ─── Caso 1 — Happy path ─────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso1_happy_path(mode):
    """Todos los pagos coinciden exactamente con las cuotas → DPD=0, deuda=0."""
    cid = "C01"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT, "REF-1"),
        pay(cid, JUL, AMOUNT, "REF-2"),
        pay(cid, AUG, AMOUNT, "REF-3"),
        pay(cid, SEP, AMOUNT, "REF-4"),
        pay(cid, OCT, AMOUNT, "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 2 — Pago parcial en la última cuota ────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso2_pago_parcial_ultima_cuota(mode):
    """Jun–Sep pagadas completas, Oct pagada al 50% → DPD solo en Oct."""
    cid = "C02"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, AMOUNT,            "REF-3"),
        pay(cid, SEP, AMOUNT,            "REF-4"),
        pay(cid, OCT, Decimal("500.00"), "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == DPD_OCT
    assert row["amount_in_arrears"] == Decimal("500.00")


# ─── Caso 3 — Sin pagos registrados ──────────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso3_sin_pagos(mode):
    """4 cuotas (Jun–Sep) sin ningún pago → DPD desde junio, deuda=$4000."""
    cid = "C03"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
    ]
    row = _run(installments, [], cid, mode)

    assert row["dpd_current"] == DPD_JUN
    assert row["amount_in_arrears"] == Decimal("4000.00")


# ─── Caso 4 — Pago atrasado ya regularizado ──────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso4_pago_atrasado_ya_regularizado(mode):
    """Ago pagada 15 días tarde pero completa; al corte todo está al día → DPD=0."""
    cid = "C04"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN,                AMOUNT, "REF-1"),
        pay(cid, JUL,                AMOUNT, "REF-2"),
        pay(cid, date(2026, 8, 16),  AMOUNT, "REF-3"),  # 15 días tarde
        pay(cid, SEP,                AMOUNT, "REF-4"),
        pay(cid, OCT,                AMOUNT, "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")



# ─── Caso 5 — Pago parcial en cuota intermedia ───────────────────────────────
# Cascade: el excedente de Jun+Jul cubre Ago → Oct queda sin fondos → DPD=1
# Join:    Ago tiene solo $500 de $1000 → Ago genera DPD=62

@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_OCT, Decimal("500.00")),
    ("join",    DPD_AUG, Decimal("500.00")),
])
def test_caso5_pago_parcial_cuota_intermedia(mode, exp_dpd, exp_arrears):
    """Jun/Jul completas, Ago 50%, Sep/Oct completas."""
    cid = "C05"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, Decimal("500.00"), "REF-3"),
        pay(cid, SEP, AMOUNT,            "REF-4"),
        pay(cid, OCT, AMOUNT,            "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 6 — Pago anticipado de cuotas ──────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso6_pago_anticipado(mode):
    """Jun pagó Jun+Jul+Ago por adelantado; Sep y Oct en sus fechas → DPD=0."""
    cid = "C06"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT, "REF-1"),  # cuota de Jun
        pay(cid, JUN, AMOUNT, "REF-2"),  # cuota de Jul pagada en Jun
        pay(cid, JUN, AMOUNT, "REF-3"),  # cuota de Ago pagada en Jun
        pay(cid, SEP, AMOUNT, "REF-4"),
        pay(cid, OCT, AMOUNT, "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 7 — Sobrepago en una cuota ─────────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso7_sobrepago_ultima_cuota(mode):
    """Jun–Sep completas, Oct pagada con $500 extra → DPD=0, deuda=0."""
    cid = "C07"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, AMOUNT,            "REF-3"),
        pay(cid, SEP, AMOUNT,            "REF-4"),
        pay(cid, OCT, Decimal("1500.00"), "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 8 — Múltiples cuotas con pago parcial ──────────────────────────────
# Cascade: pool $3500 cubre Jun+Jul+Ago completas → Sep y Oct quedan sin fondos
# Join:    Ago/Sep/Oct tienen $500 c/u → las tres en mora desde Ago

@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_SEP, Decimal("1500.00")),
    ("join",    DPD_AUG, Decimal("1500.00")),
])
def test_caso8_multiples_pagos_parciales(mode, exp_dpd, exp_arrears):
    """Jun/Jul completas, Ago/Sep/Oct al 50% c/u."""
    cid = "C08"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, Decimal("500.00"), "REF-3"),
        pay(cid, SEP, Decimal("500.00"), "REF-4"),
        pay(cid, OCT, Decimal("500.00"), "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 9 — Excedente de Sep cubre parcialmente Oct ────────────────────────
# Cascade: pool $4500 cubre Jun–Sep + $500 de Oct → Oct con $500 deuda, DPD=1
# Join:    Sep tiene $1500 (cubierta), Oct tiene $0 → Oct con $1000 deuda, DPD=1

@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_OCT, Decimal("500.00")),
    ("join",    DPD_OCT, Decimal("1000.00")),
])
def test_caso9_excedente_sep_cubre_parcialmente_oct(mode, exp_dpd, exp_arrears):
    """Jun–Ago completas, Sep pagada en 1.5×, Oct sin pago."""
    cid = "C09"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, AMOUNT,            "REF-3"),
        pay(cid, SEP, Decimal("1500.00"), "REF-4"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 10 — Cuota pagada en dos partes ────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso10_cuota_en_dos_partes(mode):
    """Jun–Sep completas; Oct en dos pagos de $500 con el mismo ref → DPD=0."""
    cid = "C10"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN,                AMOUNT,            "REF-1"),
        pay(cid, JUL,                AMOUNT,            "REF-2"),
        pay(cid, AUG,                AMOUNT,            "REF-3"),
        pay(cid, SEP,                AMOUNT,            "REF-4"),
        pay(cid, OCT,                Decimal("500.00"), "REF-5"),
        pay(cid, date(2026, 10, 2),  Decimal("500.00"), "REF-5"),  # segundo pago mismo ref
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 11 — Mora prolongada con pago parcial reciente ─────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso11_mora_prolongada_pago_parcial_reciente(mode):
    """Jun/Jul/Ago sin pago; Sep paga $1000 (equivale a Jun); Oct sin pago.
    DPD desde Jul (la más antigua impaga después de cubrir Jun). Deuda=$4000."""
    cid = "C11"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    # El pago de Sep cubre la cuota de Jun (ref REF-1 en join; pool en cascade)
    payments = [
        pay(cid, SEP, AMOUNT, "REF-1"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == DPD_JUL
    assert row["amount_in_arrears"] == Decimal("4000.00")


# ─── Caso 12 — Pago el mismo día del corte ───────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso12_pago_mismo_dia_corte(mode):
    """Oct pagada el 3-Oct (día del corte) → se considera al día → DPD=0."""
    cid = "C12"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN,       AMOUNT, "REF-1"),
        pay(cid, JUL,       AMOUNT, "REF-2"),
        pay(cid, AUG,       AMOUNT, "REF-3"),
        pay(cid, SEP,       AMOUNT, "REF-4"),
        pay(cid, CALC_DATE, AMOUNT, "REF-5"),  # pago el día del corte
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 13 — Diferencia de centavos por redondeo ───────────────────────────

@pytest.mark.parametrize("mode,paid_threshold,exp_dpd,exp_arrears", [
    ("cascade", 1.0,  DPD_OCT, Decimal("0.50")),  # estricto: $0.50 < $1000 → mora
    ("join",    1.0,  DPD_OCT, Decimal("0.50")),
    ("cascade", 0.95, 0,       Decimal("0")),      # tolerante: $999.50 ≥ $950 → al día
    ("join",    0.95, 0,       Decimal("0")),
])
def test_caso13_diferencia_centavos_redondeo(mode, paid_threshold, exp_dpd, exp_arrears):
    """Oct pagada con $0.50 de diferencia. Con threshold=1.0 genera DPD; con 0.95 no."""
    cid = "C13"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, AMOUNT,            "REF-3"),
        pay(cid, SEP, AMOUNT,            "REF-4"),
        pay(cid, OCT, Decimal("999.50"), "REF-5"),  # $0.50 menos
    ]
    row = _run(installments, payments, cid, mode, paid_threshold=paid_threshold)

    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 14 — Crédito reestructurado a mitad de período ─────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso14_credito_reestructurado(mode):
    """Jun/Jul pagadas. En Aug se reestructura: Aug se elimina, Sep/Oct bajan a $800.
    El nuevo schedule refleja las cuotas actualizadas → DPD=0, deuda=0."""
    cid = "C14"
    new_amount = Decimal("800.00")
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        # Aug eliminado por reestructuración; Sep y Oct con nuevos montos
        inst(cid, 3, SEP, "REF-3", gross=new_amount),
        inst(cid, 4, OCT, "REF-4", gross=new_amount),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,      "REF-1"),
        pay(cid, JUL, AMOUNT,      "REF-2"),
        pay(cid, SEP, new_amount,  "REF-3"),
        pay(cid, OCT, new_amount,  "REF-4"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 15 — Pago duplicado ────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso15_pago_duplicado(mode):
    """Ago pagada dos veces ($2000); el resto correcto → DPD=0, deuda=0."""
    cid = "C15"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT,            "REF-1"),
        pay(cid, JUL, AMOUNT,            "REF-2"),
        pay(cid, AUG, AMOUNT,            "REF-3"),  # primer pago
        pay(cid, AUG, AMOUNT,            "REF-3"),  # duplicado mismo ref
        pay(cid, SEP, AMOUNT,            "REF-4"),
        pay(cid, OCT, AMOUNT,            "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == 0
    assert row["amount_in_arrears"] == Decimal("0")


# ─── Caso 16 — Primera cuota nunca pagada ────────────────────────────────────
# Cascade: pool $4000 (Jul–Oct) se aplica FIFO: Jun✓ Jul✓ Aug✓ Sep✓ Oct sin fondos
# Join:    Jun tiene $0 de su ref → Jun en mora desde el inicio

@pytest.mark.parametrize("mode,exp_dpd,exp_arrears", [
    ("cascade", DPD_OCT, Decimal("1000.00")),
    ("join",    DPD_JUN, Decimal("1000.00")),
])
def test_caso16_primera_cuota_nunca_pagada(mode, exp_dpd, exp_arrears):
    """Jun nunca pagada; Jul–Oct completas y a tiempo."""
    cid = "C16"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        # Sin pago para REF-1 (Jun)
        pay(cid, JUL, AMOUNT, "REF-2"),
        pay(cid, AUG, AMOUNT, "REF-3"),
        pay(cid, SEP, AMOUNT, "REF-4"),
        pay(cid, OCT, AMOUNT, "REF-5"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == exp_dpd
    assert row["amount_in_arrears"] == exp_arrears


# ─── Caso 17 — Contrato sin payment tape ─────────────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso17_sin_payment_tape(mode):
    """Contrato existe en SPI pero no tiene ningún pago → DPD desde Jun, deuda=$4000."""
    cid = "C17"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
    ]
    row = _run(installments, [], cid, mode)

    assert row["dpd_current"] == DPD_JUN
    assert row["amount_in_arrears"] == Decimal("4000.00")


# ─── Caso 18 — Pagos normales y luego abandono ───────────────────────────────

@pytest.mark.parametrize("mode", ["cascade", "join"])
def test_caso18_abandono_desde_sep(mode):
    """Jun–Ago completas y a tiempo; Sep y Oct sin pago → DPD desde Sep, deuda=$2000."""
    cid = "C18"
    installments = [
        inst(cid, 1, JUN, "REF-1"),
        inst(cid, 2, JUL, "REF-2"),
        inst(cid, 3, AUG, "REF-3"),
        inst(cid, 4, SEP, "REF-4"),
        inst(cid, 5, OCT, "REF-5"),
    ]
    payments = [
        pay(cid, JUN, AMOUNT, "REF-1"),
        pay(cid, JUL, AMOUNT, "REF-2"),
        pay(cid, AUG, AMOUNT, "REF-3"),
    ]
    row = _run(installments, payments, cid, mode)

    assert row["dpd_current"] == DPD_SEP
    assert row["amount_in_arrears"] == Decimal("2000.00")
