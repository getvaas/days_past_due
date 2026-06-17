"""Tests de resolución de DBConfig por entorno (config.py).

Núcleo puro: no pega a AWS — boto3 se mockea. Cubre el parser de URL,
from_secrets_manager, el despacho de load() y el cacheo del secret.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from dpd import config
from dpd.config import DBConfig, _parse_db_url


@pytest.fixture(autouse=True)
def _clear_secret_cache():
    """El cache de _load_secret_values es global: limpiarlo entre tests."""
    config._load_secret_values.cache_clear()
    yield
    config._load_secret_values.cache_clear()


# ─── _parse_db_url ──────────────────────────────────────────────────────────

def test_parse_db_url_jdbc_scheme():
    assert _parse_db_url("jdbc:mysql://db.host:3306/payments_db") == ("db.host", 3306, "payments_db")


def test_parse_db_url_mysql_scheme():
    assert _parse_db_url("mysql://db.host:3307/payments_db") == ("db.host", 3307, "payments_db")


def test_parse_db_url_no_scheme():
    assert _parse_db_url("db.host:3306/payments_db") == ("db.host", 3306, "payments_db")


def test_parse_db_url_default_port():
    assert _parse_db_url("mysql://db.host/payments_db") == ("db.host", 3306, "payments_db")


def test_parse_db_url_ignores_query_params():
    assert _parse_db_url("jdbc:mysql://db.host:3306/payments_db?useSSL=false&x=1") == (
        "db.host", 3306, "payments_db",
    )


@pytest.mark.parametrize("bad", ["", "not a url", "mysql://db.host:3306/"])
def test_parse_db_url_invalid_raises(bad):
    with pytest.raises(RuntimeError):
        _parse_db_url(bad)


# ─── from_secrets_manager ─────────────────────────────────────────────────────

def _secret_payload(url="jdbc:mysql://db.host:3306/payments_db"):
    return {
        "DATASOURCE___PAYMENTS_DB___URL": url,
        "DATASOURCE___PAYMENTS_DB___USERNAME": "payuser",
        "DATASOURCE___PAYMENTS_DB___PASSWORD": "paypass",
    }


def test_from_secrets_manager_builds_config():
    with patch("boto3.client") as mock_client:
        mock_client.return_value.get_secret_value.return_value = {
            "SecretString": json.dumps(_secret_payload()),
        }
        cfg = DBConfig.from_secrets_manager(secret_name="dev/payments/datasource")

    assert cfg == DBConfig(
        host="db.host", port=3306, dbname="payments_db",
        user="payuser", password="paypass",
    )


def test_from_secrets_manager_missing_secret_name_raises(monkeypatch):
    monkeypatch.delenv("PAYMENTS_SECRET_NAME", raising=False)
    with pytest.raises(RuntimeError, match="PAYMENTS_SECRET_NAME"):
        DBConfig.from_secrets_manager()


def test_from_secrets_manager_missing_key_raises():
    payload = _secret_payload()
    del payload["DATASOURCE___PAYMENTS_DB___PASSWORD"]
    with patch("boto3.client") as mock_client:
        mock_client.return_value.get_secret_value.return_value = {
            "SecretString": json.dumps(payload),
        }
        with pytest.raises(RuntimeError, match="claves requeridas"):
            DBConfig.from_secrets_manager(secret_name="dev/payments/datasource")


def test_secret_read_cached_once():
    """Varias resoluciones en el mismo run → un solo GetSecretValue."""
    with patch("boto3.client") as mock_client:
        mock_client.return_value.get_secret_value.return_value = {
            "SecretString": json.dumps(_secret_payload()),
        }
        DBConfig.from_secrets_manager(secret_name="dev/payments/datasource")
        DBConfig.from_secrets_manager(secret_name="dev/payments/datasource")

    assert mock_client.return_value.get_secret_value.call_count == 1


# ─── load() — despacho por entorno ────────────────────────────────────────────

def test_load_uses_secrets_manager_in_lambda(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "dev-days-past-due-lambda")
    sentinel = DBConfig("h", 3306, "d", "u", "p")
    with patch.object(DBConfig, "from_secrets_manager", return_value=sentinel) as m_sm, \
         patch.object(DBConfig, "from_env") as m_env:
        assert DBConfig.load() is sentinel
    m_sm.assert_called_once()
    m_env.assert_not_called()


def test_load_uses_env_locally(monkeypatch):
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    sentinel = DBConfig("localhost", 3306, "d", "u", "p")
    with patch.object(DBConfig, "from_env", return_value=sentinel) as m_env, \
         patch.object(DBConfig, "from_secrets_manager") as m_sm:
        assert DBConfig.load() is sentinel
    m_env.assert_called_once()
    m_sm.assert_not_called()
