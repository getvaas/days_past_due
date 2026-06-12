"""Lectura y escritura del loan tape en S3.

Soporta CSV y Parquet según la extensión del path.
"""
from __future__ import annotations

import io
from typing import Optional

import boto3
import pandas as pd


def _s3_client():
    return boto3.client("s3")


def _parse_s3_path(s3_path: str) -> tuple[str, str]:
    """Descompone 's3://bucket/key' en (bucket, key)."""
    if not s3_path.startswith("s3://"):
        raise ValueError(f"Path S3 inválido: {s3_path}")
    path = s3_path[5:]
    bucket, _, key = path.partition("/")
    return bucket, key


def read_loan_tape(s3_path: str) -> pd.DataFrame:
    """Lee el loan tape desde S3. Soporta .csv y .parquet."""
    bucket, key = _parse_s3_path(s3_path)
    s3 = _s3_client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj["Body"].read()

    if key.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(content))
    else:
        return pd.read_csv(io.BytesIO(content))


def try_read_loan_tape(s3_path: str) -> Optional[pd.DataFrame]:
    """Lee el loan tape desde S3. Devuelve None si el objeto no existe (NoSuchKey).

    Usado para leer el output anterior y recuperar dpd_max del run previo.
    """
    try:
        return read_loan_tape(s3_path)
    except Exception as exc:
        # boto3 lanza ClientError con response["Error"]["Code"] == "NoSuchKey"
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            code = response.get("Error", {}).get("Code", "")
            if code == "NoSuchKey":
                return None
        raise


def write_loan_tape(df: pd.DataFrame, s3_path: str) -> None:
    """Escribe el loan tape enriquecido en S3. Soporta .csv y .parquet."""
    bucket, key = _parse_s3_path(s3_path)
    s3 = _s3_client()

    buffer = io.BytesIO()
    if key.endswith(".parquet"):
        df.to_parquet(buffer, index=False)
        content_type = "application/octet-stream"
    else:
        df.to_csv(buffer, index=False)
        content_type = "text/csv"

    buffer.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue(), ContentType=content_type)
