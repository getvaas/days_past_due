"""Tests de cableado (Fase 3): lambda_handler y db_excel_runner usan los loaders
canónicos y resuelven la compañía. Todo mockeado — sin BD, AWS ni red.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pandas as pd

from dpd.config import DBConfig
from dpd.models import InboundMessage, MessageMetadata


def _inbound(target_id=143, products=None):
    return InboundMessage(
        origin="ENRICHER", target="PAYMENTS_EXPAND", job_id="j1",
        input_file="s3://b/in.csv", output_file="s3://b/out.csv",
        key="contract_id", target_type="COMPANY", target_id=target_id,
        metadata=MessageMetadata(products=products or []),
    )


def test_process_message_resolves_company_and_loads_from_db():
    from dpd import lambda_handler

    loan_tape = pd.DataFrame({"contract_id": ["C1"]})
    spi = pd.DataFrame({"borrower_contract_id": ["C1"], "id": [1]})
    pays = pd.DataFrame(columns=["borrower_contract_id", "payment_date", "total_payment"])
    last = {"last_payment_tape_date": None, "last_schedule_payment_date": None, "last_payment_date": None}

    with patch.object(lambda_handler, "read_loan_tape", return_value=loan_tape), \
         patch.object(lambda_handler, "try_read_loan_tape", return_value=None), \
         patch.object(lambda_handler, "CompanyClient") as MockCC, \
         patch.object(lambda_handler, "load_schedule", return_value=spi) as m_sched, \
         patch.object(lambda_handler, "load_payment_tape", return_value=pays) as m_pay, \
         patch.object(lambda_handler, "write_loan_tape") as m_write, \
         patch.object(lambda_handler, "read_last_dates", return_value=last), \
         patch.object(lambda_handler, "publish_response", return_value="mid"):
        MockCC.return_value.get_company_by_id.return_value = "ADDI"
        lambda_handler._process_message(_inbound(target_id=143))

    MockCC.return_value.get_company_by_id.assert_called_once_with(143)
    m_sched.assert_called_once_with("ADDI")
    m_pay.assert_called_once_with(143)
    m_write.assert_called_once()


def test_process_message_raises_when_company_code_unresolved():
    from dpd import lambda_handler
    import pytest

    with patch.object(lambda_handler, "read_loan_tape", return_value=pd.DataFrame({"contract_id": ["C1"]})), \
         patch.object(lambda_handler, "try_read_loan_tape", return_value=None), \
         patch.object(lambda_handler, "CompanyClient") as MockCC:
        MockCC.return_value.get_company_by_id.return_value = None
        with pytest.raises(RuntimeError, match="company_code"):
            lambda_handler._process_message(_inbound(target_id=999))


def test_run_from_db_uses_canonical_loaders():
    from dpd.integrations import db_excel_runner as r

    cfg = DBConfig(host="h", port=3306, dbname="d", user="u", password="p")
    sched = pd.DataFrame({"borrower_contract_id": ["C1"]})
    pays = pd.DataFrame({"borrower_contract_id": ["C1"]})

    with patch.object(r, "_db_config", return_value=cfg), \
         patch.object(r, "load_schedule", return_value=sched) as m_s, \
         patch.object(r, "load_payment_tape", return_value=pays) as m_p, \
         patch.object(r, "compute_dpd", return_value=(sched, sched)):
        r.run_from_db(company_id=143, company_code="ADDI", calc_date=dt.date(2026, 6, 1))

    m_s.assert_called_once_with("ADDI", db_cfg=cfg)
    m_p.assert_called_once_with(143, db_cfg=cfg)
