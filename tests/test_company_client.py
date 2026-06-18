"""Tests del CompanyClient (resolución de compañía).

Sin red: se mockean el token M2M, el secrets_manager y la sesión HTTP.
Cubre el nuevo get_company_by_id (id→code) y, de sanidad, get_borrower_id_by_code (code→id).
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from dpd.clients.company_client import CompanyClient


def _mock_response(payload, status=200):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.status_code = status
    resp.headers = {}
    resp.raise_for_status.return_value = None
    return resp


@contextmanager
def _client():
    """CompanyClient con token y secret mockeados; sesión HTTP reemplazable."""
    with patch("dpd.clients.company_client.machine_to_machine.get_token", return_value="tok"), \
         patch("dpd.clients.company_client.secrets_manager.get_secret_value", return_value="vaas"):
        c = CompanyClient(base_url="http://company.test/api")
        c._session = MagicMock()
        yield c


def test_get_company_by_id_returns_code():
    with _client() as c:
        c._session.get.return_value = _mock_response([{"id": 143, "code": "ADDI", "name": "Addi"}])
        assert c.get_company_by_id(143) == "ADDI"
        c._session.get.assert_called_once()


def test_get_company_by_id_not_found_returns_none():
    with _client() as c:
        c._session.get.return_value = _mock_response([])
        assert c.get_company_by_id(999) is None


def test_get_company_by_id_passes_id_param():
    with _client() as c:
        c._session.get.return_value = _mock_response([{"id": 143, "code": "ADDI"}])
        c.get_company_by_id(143)
        _, kwargs = c._session.get.call_args
        assert kwargs["params"] == {"id": 143}


def test_get_borrower_id_by_code_returns_id():
    with _client() as c:
        c._session.get.return_value = _mock_response([{"id": 143, "code": "ADDI"}])
        assert c.get_borrower_id_by_code("ADDI") == 143
