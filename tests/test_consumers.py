"""Tests de cableado: lambda_handler usa los loaders canónicos con company_id
directo. Todo mockeado — sin BD, AWS ni red.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pandas as pd
import polars as pl

from dpd.models import InboundMessage, MessageMetadata


def _inbound(target_id=143, products=None):
    return InboundMessage(
        origin="ENRICHER", target="PAYMENTS_EXPAND", job_id="j1",
        input_file="s3://b/in.csv", output_file="s3://b/out.csv",
        key="contract_id", target_type="COMPANY", target_id=target_id,
        metadata=MessageMetadata(products=products or []),
    )

def test_process_message_loads_from_db_with_company_id():
    from dpd import lambda_handler

    loan_tape = pl.DataFrame({"contract_id": ["C1"]})
    spi = pd.DataFrame({"borrower_contract_id": ["C1"], "id": [1]})
    pays = pd.DataFrame(columns=["borrower_contract_id", "payment_date", "total_payment"])
    last = {"last_payment_tape_date": None, "last_schedule_payment_date": None, "last_payment_date": None}

    with patch.object(lambda_handler, "read_loan_tape", return_value=loan_tape), \
         patch.object(lambda_handler, "load_schedule", return_value=spi) as m_sched, \
         patch.object(lambda_handler, "load_payment_tape", return_value=pays) as m_pay, \
         patch.object(lambda_handler, "write_loan_tape") as m_write, \
         patch.object(lambda_handler, "read_last_dates", return_value=last), \
         patch.object(lambda_handler, "publish_response", return_value="mid"):
        lambda_handler._process_message(_inbound(target_id=143))

    m_sched.assert_called_once_with(143)
    m_pay.assert_called_once_with(143)
    m_write.assert_called_once()


def test_batch_config_defaults():
    import os
    from unittest.mock import patch
    # Verificar que las constantes tienen los valores default cuando las env vars no están seteadas.
    env = {k: v for k, v in os.environ.items()
           if k not in ("BATCH_ROW_THRESHOLD", "BATCH_JOB_QUEUE", "BATCH_JOB_DEFINITION")}
    with patch.dict(os.environ, env, clear=True):
        import importlib
        import dpd.config.config as cfg_mod
        importlib.reload(cfg_mod)
        assert cfg_mod.BATCH_ROW_THRESHOLD == 5000
        assert cfg_mod.BATCH_JOB_QUEUE == ""
        assert cfg_mod.BATCH_JOB_DEFINITION == ""


def test_lambda_under_threshold_processes_inline():
    from dpd import lambda_handler, config

    rows = [{"contract_id": f"C{i}"} for i in range(3)]
    loan_tape = pl.DataFrame(rows)
    spi = pd.DataFrame({"borrower_contract_id": ["C0"], "id": [1]})
    pays = pd.DataFrame(columns=["borrower_contract_id", "payment_date", "total_payment"])
    last = {"last_payment_tape_date": None, "last_schedule_payment_date": None, "last_payment_date": None}

    with patch.object(lambda_handler, "read_loan_tape", return_value=loan_tape), \
         patch.object(lambda_handler, "load_schedule", return_value=spi), \
         patch.object(lambda_handler, "load_payment_tape", return_value=pays), \
         patch.object(lambda_handler, "write_loan_tape"), \
         patch.object(lambda_handler, "read_last_dates", return_value=last), \
         patch.object(lambda_handler, "publish_response", return_value="mid") as m_sns, \
         patch.object(lambda_handler, "submit_job") as m_batch, \
         patch.object(config, "BATCH_ROW_THRESHOLD", 5):
        lambda_handler._process_message(_inbound())

    m_sns.assert_called_once()
    m_batch.assert_not_called()


def test_lambda_over_threshold_submits_batch():
    from dpd import lambda_handler, config

    rows = [{"contract_id": f"C{i}"} for i in range(10)]
    loan_tape = pl.DataFrame(rows)

    with patch.object(lambda_handler, "read_loan_tape", return_value=loan_tape), \
         patch.object(lambda_handler, "submit_job") as m_batch, \
         patch.object(lambda_handler, "publish_response") as m_sns, \
         patch.object(config, "BATCH_ROW_THRESHOLD", 5), \
         patch.object(config, "BATCH_JOB_QUEUE", "test-queue"), \
         patch.object(config, "BATCH_JOB_DEFINITION", "test-def"):
        lambda_handler._process_message(_inbound())

    m_batch.assert_called_once()
    call_kwargs = m_batch.call_args
    assert call_kwargs[0][1] == "test-queue"
    assert call_kwargs[0][2] == "test-def"
    m_sns.assert_not_called()


def test_batch_handler_runs_process_message():
    from dpd import batch_handler

    payload = {
        "origin": "ENRICHER", "target": "PAYMENTS_EXPAND",
        "job_id": "batch-001", "input_file": "s3://b/in.csv",
        "output_file": "s3://b/out.csv", "key": "contract_id",
        "target_type": "COMPANY", "target_id": 143, "rate_type": "fixed",
        "metadata": {"products": []},
    }
    with patch("dpd.batch_handler._process_message") as m_proc, \
         patch("dpd.batch_handler._validate"):
        rc = batch_handler.main(["--payload", __import__("json").dumps(payload)])

    assert rc == 0
    m_proc.assert_called_once()
    called_msg = m_proc.call_args[0][0]
    assert called_msg.job_id == "batch-001"
    assert called_msg.target_id == 143


def test_local_runner_dry_run_parses_event(tmp_path):
    from dpd.local_runner import main

    event = {
        "origin": "ENRICHER", "target": "PAYMENTS_EXPAND",
        "job_id": "test-001", "input_file": "s3://b/in.csv",
        "output_file": "s3://b/out.csv", "key": "contract_id",
        "target_type": "COMPANY", "target_id": 143, "rate_type": "fixed",
        "metadata": {"products": ["dpd"]},
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(__import__("json").dumps(event))

    rc = main(["--event", str(event_file), "--dry-run"])
    assert rc == 0


def test_local_runner_calls_handler(tmp_path):
    from dpd import local_runner
    from unittest.mock import patch

    event = {
        "origin": "ENRICHER", "target": "PAYMENTS_EXPAND",
        "job_id": "test-002", "input_file": "s3://b/in.csv",
        "output_file": "s3://b/out.csv", "key": "contract_id",
        "target_type": "COMPANY", "target_id": 143, "rate_type": "fixed",
        "metadata": {"products": []},
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(__import__("json").dumps(event))

    import json as _json
    payload = _json.loads(event_file.read_text())

    with patch("dpd.local_runner.handler", return_value={"statusCode": 200, "processed": 1}) as m_handler:
        result = local_runner.run(payload)

    assert result["statusCode"] == 200
    called_event = m_handler.call_args[0][0]
    assert len(called_event["Records"]) == 1
    assert _json.loads(called_event["Records"][0]["body"])["job_id"] == "test-002"


