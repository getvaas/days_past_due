"""Tests de los loaders BD canónicos de excel_runner.

Sin BD real: se mockean connect/cursor. Verifican que load_schedule/load_payment_tape
leen, sanitizan y filtran por la compañía, y que _payments_from_df descarta inválidos.
"""
from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pandas as pd

from dpd import excel_runner
from dpd.config import DBConfig

DUMMY_CFG = DBConfig(host="h", port=3306, dbname="d", user="u", password="p")


@contextmanager
def _mock_db(rows):
    """Mockea excel_runner.connect/cursor; devuelve el cursor para inspeccionar execute."""
    cur = MagicMock()
    cur.fetchall.return_value = rows

    @contextmanager
    def fake_cursor(conn, dict_rows=True):
        yield cur

    with patch("dpd.excel_runner.connect", return_value=MagicMock()), \
         patch("dpd.excel_runner.cursor", fake_cursor):
        yield cur


def test_load_schedule_reads_and_sanitizes():
    rows = [{
        "id": 1, "company_id": 42, "borrower_contract_id": "C001",
        "borrower_installment_reference": "C001-1", "date": "2026-02-01",
        "gross_amount": 1000, "guarantee_amount": 0, "principal_amount": 800,
        "interest_amount": 150, "tax_amount": 30, "fee_amount": 20,
    }]
    with _mock_db(rows):
        df = excel_runner.load_schedule(42, db_cfg=DUMMY_CFG)

    assert len(df) == 1
    assert df.loc[0, "date"] == dt.date(2026, 2, 1)            # sanitizado a date
    assert df.loc[0, "borrower_installment_reference"] == "C001-1"  # ref a str


def test_load_schedule_empty_returns_empty_df():
    with _mock_db([]):
        df = excel_runner.load_schedule(99, db_cfg=DUMMY_CFG)
    assert df.empty


def test_load_schedule_filters_by_company_id():
    with _mock_db([]) as cur:
        excel_runner.load_schedule(42, db_cfg=DUMMY_CFG)
    sql, params = cur.execute.call_args[0]
    assert params == {"company_id": 42}


def test_load_payment_tape_reads_and_sanitizes():
    rows = [{
        "id": 1, "company_id": 42, "borrower_contract_id": "C001",
        "borrower_installment_reference": "C001-1",
        "payment_date": "2026-02-01", "total_payment": 1000,
    }]
    with _mock_db(rows):
        df = excel_runner.load_payment_tape(42, db_cfg=DUMMY_CFG)

    assert df.loc[0, "payment_date"] == dt.date(2026, 2, 1)
    assert df.loc[0, "total_payment"] == 1000


def test_load_payment_tape_empty_returns_min_cols():
    with _mock_db([]):
        df = excel_runner.load_payment_tape(99, db_cfg=DUMMY_CFG)
    assert df.empty
    assert list(df.columns) == excel_runner._PT_MIN_COLS


def test_load_payment_tape_filters_by_company_id():
    with _mock_db([]) as cur:
        excel_runner.load_payment_tape(42, db_cfg=DUMMY_CFG)
    sql, params = cur.execute.call_args[0]
    assert params == {"company_id": 42}


def test_payments_from_df_discards_invalid():
    df = pd.DataFrame([
        {"borrower_contract_id": "C1", "borrower_installment_reference": "r1",
         "payment_date": dt.date(2026, 2, 1), "total_payment": 100},
        {"borrower_contract_id": "C1", "borrower_installment_reference": "r2",
         "payment_date": None, "total_payment": 100},            # NaT → descartado
        {"borrower_contract_id": "C1", "borrower_installment_reference": "r3",
         "payment_date": dt.date(2026, 2, 1), "total_payment": 0},  # <= 0 → descartado
    ])
    out = excel_runner._payments_from_df(df)
    assert len(out) == 1
    assert out[0]["borrower_installment_reference"] == "r1"
