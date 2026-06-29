"""Tests de los loaders BD canónicos de db_reader.

Sin BD real: se mockean connect/cursor. Verifican que load_schedule/load_payment_tape
leen, sanitizan y filtran por la compañía, devolviendo polars DataFrames.
"""
from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import polars as pl

from dpd import db_reader
from dpd.config import DBConfig
from dpd.products import dpd as dpd_product

DUMMY_CFG = DBConfig(host="h", port=3306, dbname="d", user="u", password="p")


@contextmanager
def _mock_db(rows):
    """Mockea db_reader.connection; devuelve el cursor para inspeccionar execute."""
    cur = MagicMock()
    cur.fetchall.return_value = rows

    @contextmanager
    def fake_connection(cfg, dict_rows=True):
        yield cur

    with patch("dpd.db_reader.connection", fake_connection):
        yield cur


def test_load_schedule_reads_and_sanitizes():
    rows = [{
        "id": 1, "company_id": 42, "borrower_contract_id": "C001",
        "borrower_installment_reference": "C001-1", "date": "2026-02-01",
        "gross_amount": 1000, "guarantee_amount": 0, "principal_amount": 800,
        "interest_amount": 150, "tax_amount": 30, "fee_amount": 20,
    }]
    with _mock_db(rows):
        df = db_reader.load_schedule(42, db_cfg=DUMMY_CFG)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["date"][0] == dt.date(2026, 2, 1)                  # sanitizado a date
    assert df["borrower_installment_reference"][0] == "C001-1"   # ref a str


def test_load_schedule_empty_returns_empty_df():
    with _mock_db([]):
        df = db_reader.load_schedule(99, db_cfg=DUMMY_CFG)
    assert df.is_empty()


def test_load_schedule_filters_by_company_id():
    with _mock_db([]) as cur:
        db_reader.load_schedule(42, db_cfg=DUMMY_CFG)
    sql, params = cur.execute.call_args[0]
    assert params == {"company_id": 42}


def test_load_payment_tape_reads_and_sanitizes():
    rows = [{
        "id": 1, "company_id": 42, "borrower_contract_id": "C001",
        "borrower_installment_reference": "C001-1",
        "payment_date": "2026-02-01", "total_payment": 1000,
    }]
    with _mock_db(rows):
        df = db_reader.load_payment_tape(42, db_cfg=DUMMY_CFG)

    assert df["payment_date"][0] == dt.date(2026, 2, 1)
    assert df["total_payment"][0] == 1000


def test_load_payment_tape_empty_returns_min_cols():
    with _mock_db([]):
        df = db_reader.load_payment_tape(99, db_cfg=DUMMY_CFG)
    assert df.is_empty()
    assert df.columns == db_reader._PT_MIN_COLS


def test_load_payment_tape_filters_by_company_id():
    with _mock_db([]) as cur:
        db_reader.load_payment_tape(42, db_cfg=DUMMY_CFG)
    sql, params = cur.execute.call_args[0]
    assert params == {"company_id": 42}


def test_payments_from_pl_discards_invalid():
    df = pl.DataFrame([
        {"borrower_contract_id": "C1", "borrower_installment_reference": "r1",
         "payment_date": dt.date(2026, 2, 1), "total_payment": 100},
        {"borrower_contract_id": "C1", "borrower_installment_reference": "r2",
         "payment_date": None, "total_payment": 100},            # sin fecha → descartado
        {"borrower_contract_id": "C1", "borrower_installment_reference": "r3",
         "payment_date": dt.date(2026, 2, 1), "total_payment": 0},  # <= 0 → descartado
    ])
    out = dpd_product._payments_from_pl(df)
    assert len(out) == 1
    assert out[0]["borrower_installment_reference"] == "r1"
