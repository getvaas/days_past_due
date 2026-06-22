"""Fixtures compartidos para los tests de integración.

Requiere el contenedor vaas_local_mysql corriendo:
    cd ~/Desktop/wks/local-infra && docker compose up -d
"""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest

from dpd.config.config import DBConfig
from dpd.integrations.db import connect

_TEST_DB_CFG = DBConfig(
    host=os.environ.get("TEST_DB_HOST", "localhost"),
    port=int(os.environ.get("TEST_DB_PORT", "3306")),
    dbname=os.environ.get("TEST_DB_NAME", "payments_db_test"),
    user=os.environ.get("TEST_DB_USER", "vaas"),
    password=os.environ.get("TEST_DB_PASSWORD", "vaas"),
)

_INSERT_SPI = """
    INSERT INTO scheduled_payments_installments
        (company_id, company_code, borrower_contract_id,
         borrower_installment_reference, `date`,
         gross_amount, principal_amount, interest_amount,
         guarantee_amount, tax_amount, fee_amount)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_INSERT_PAY = """
    INSERT INTO payment_tape
        (company_id, borrower_contract_id,
         borrower_installment_reference, payment_date, total_payment)
    VALUES (%s, %s, %s, %s, %s)
"""


@pytest.fixture(scope="session")
def db_cfg():
    """DBConfig apuntando a payments_db_test. Skipea la sesión si la DB no está disponible."""
    try:
        conn = connect(_TEST_DB_CFG)
        conn.close()
    except Exception as exc:
        pytest.skip(f"payments_db_test no disponible: {exc} — levantá docker compose en local-infra/")
    return _TEST_DB_CFG


@pytest.fixture
def db(db_cfg):
    """Conexión limpia para cada test — trunca ambas tablas antes de ceder control."""
    conn = connect(db_cfg)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE payment_tape")
        cur.execute("TRUNCATE TABLE scheduled_payments_installments")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def insert(db):
    """Helpers de inserción atados a la conexión limpia del test."""

    def installment(
        company_id: int,
        cid: str,
        ref: str,
        due: date,
        gross: Decimal = Decimal("1000.00"),
    ) -> None:
        with db.cursor() as cur:
            cur.execute(_INSERT_SPI, (
                company_id, str(company_id), cid, ref, due,
                gross, gross, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"),
            ))
        db.commit()

    def payment(
        company_id: int,
        cid: str,
        ref: str | None,
        pdate: date,
        amount: Decimal,
    ) -> None:
        with db.cursor() as cur:
            cur.execute(_INSERT_PAY, (company_id, cid, ref, pdate, amount))
        db.commit()

    return type("Inserter", (), {"installment": staticmethod(installment),
                                  "payment": staticmethod(payment)})()
