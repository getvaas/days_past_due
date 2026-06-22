"""Utilidades S3 — lectura y escritura del loan tape, y subida de strings.

Usa aws_boto_session para soportar AWS_PROFILE_NAME en ejecuciones locales.
Soporta CSV y Parquet según la extensión del path.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

import pandas as pd

from . import aws_boto_session

log = logging.getLogger(__name__)


def _parse_s3_path(s3_path: str) -> tuple[str, str]:
    """Descompone 's3://bucket/key' en (bucket, key)."""
    if not s3_path.startswith("s3://"):
        raise ValueError(f"Path S3 inválido: {s3_path!r}")
    path = s3_path[5:]
    bucket, _, key = path.partition("/")
    return bucket, key


def read_loan_tape(s3_path: str, config=None) -> pd.DataFrame:
    """Lee el loan tape desde S3. Soporta .csv y .parquet."""
    bucket, key = _parse_s3_path(s3_path)
    s3 = aws_boto_session.get_s3_client(config) if config else __import__("boto3").client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj["Body"].read()
    log.info("Leído s3://%s/%s (%d bytes)", bucket, key, len(content))

    if key.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(content))
    return pd.read_csv(io.BytesIO(content))


def try_read_loan_tape(s3_path: str, config=None) -> Optional[pd.DataFrame]:
    """Lee el loan tape desde S3. Devuelve None si el objeto no existe (NoSuchKey).

    Usado para leer el output anterior y recuperar dpd_max del run previo.
    """
    try:
        return read_loan_tape(s3_path, config=config)
    except Exception as exc:
        response = getattr(exc, "response", None)
        if isinstance(response, dict) and response.get("Error", {}).get("Code") == "NoSuchKey":
            return None
        raise


def write_loan_tape(df: pd.DataFrame, s3_path: str, config=None) -> None:
    """Escribe el loan tape enriquecido en S3. Soporta .csv y .parquet."""
    bucket, key = _parse_s3_path(s3_path)
    s3 = aws_boto_session.get_s3_client(config) if config else __import__("boto3").client("s3")

    buffer = io.BytesIO()
    if key.endswith(".parquet"):
        df.to_parquet(buffer, index=False)
        content_type = "application/octet-stream"
    else:
        df.to_csv(buffer, index=False)
        content_type = "text/csv"

    buffer.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue(), ContentType=content_type)
    log.info("Escrito s3://%s/%s", bucket, key)


def upload_string(bucket: str, key: str, string: str, config=None) -> None:
    """Sube un string a S3 en el bucket/key indicados."""
    s3 = aws_boto_session.get_s3_client(config) if config else __import__("boto3").client("s3")
    s3.put_object(Body=string, Bucket=bucket, Key=key)
    log.info("Subido string a s3://%s/%s", bucket, key)
