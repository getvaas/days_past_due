"""Helper para leer valores de AWS Secrets Manager.

El secret (nombre en config.VAAS_SECRET_NAME) es un JSON; get_secret_value(key)
devuelve la clave pedida. Cacheado: un solo GetSecretValue por secret por proceso.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Optional

from .. import config
from . import aws_boto_session

log = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _load_secret(secret_name: str) -> dict:
    client = aws_boto_session.get_secrets_client(config)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def get_secret_value(key: str, secret_name: Optional[str] = None) -> Optional[str]:
    """Devuelve el valor de `key` dentro del secret JSON. None si no se puede resolver."""
    name = secret_name or config.VAAS_SECRET_NAME
    if not name:
        log.warning("VAAS_SECRET_NAME no configurado; no se puede leer %s", key)
        return None
    try:
        values = _load_secret(name)
    except Exception as exc:  # noqa: BLE001 — degradar a None y loguear
        log.error("No se pudo leer el secret %r: %s", name, exc)
        return None
    return values.get(key)
