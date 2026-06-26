"""Runtime config for the DPD job.

DB credentials come from two sources depending on the environment:
- **Local** (sin AWS_LAMBDA_FUNCTION_NAME): variables de entorno, auto-cargadas
  desde el .env en la raíz del repo.
- **Lambda** (AWS_LAMBDA_FUNCTION_NAME presente): se leen de un secret en AWS
  Secrets Manager (nombre/ARN en PAYMENTS_SECRET_NAME).

`DBConfig.load()` es el resolutor que elige la fuente según el entorno.
Calculation parameters come from the CLI and are passed around as a dataclass.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


def _load_dotenv(path: Path) -> None:
    """Carga KEY=VALUE de un .env al environment.

    Pisa cualquier valor ya seteado: el .env es la fuente de verdad para este
    proyecto local y queremos evitar que un `source .env` previo en zsh (que
    expande $vars) deje credenciales corruptas en el shell.
    """
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching surrounding quotes (no recursive strip).
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key:
            os.environ[key] = value


_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


AWS_PROFILE_NAME = os.environ.get("AWS_PROFILE_NAME") or None

# True cuando NO corre en Lambda (AWS inyecta AWS_LAMBDA_FUNCTION_NAME).
LOCAL_ENV = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None

# ── AWS Batch ──
BATCH_ROW_THRESHOLD: int = int(os.environ.get("BATCH_ROW_THRESHOLD", "5000"))
BATCH_JOB_QUEUE: str = os.environ.get("BATCH_JOB_QUEUE", "")
BATCH_JOB_DEFINITION: str = os.environ.get("BATCH_JOB_DEFINITION", "")


# Claves esperadas dentro del JSON del secret de Payments (Secrets Manager).
_SECRET_KEY_URL = "DATASOURCE___PAYMENTS_DB___URL"
_SECRET_KEY_USER = "DATASOURCE___PAYMENTS_DB___USERNAME"
_SECRET_KEY_PASSWORD = "DATASOURCE___PAYMENTS_DB___PASSWORD"


def _parse_db_url(url: str) -> tuple[str, int, str]:
    """Parsea una URL de conexión MySQL en (host, port, dbname).

    Acepta `jdbc:mysql://host:3306/db`, `mysql://host:3306/db` y `host:3306/db`.
    Puerto por defecto 3306 si no viene. Ignora query params (ej. ?useSSL=false).
    """
    raw = (url or "").strip()
    if raw.lower().startswith("jdbc:"):
        raw = raw[len("jdbc:"):]
    # Si no hay esquema, anteponer '//' para que urlparse llene el netloc.
    if "://" not in raw:
        raw = "//" + raw

    try:
        parsed = urlparse(raw)
        host = parsed.hostname
        port = parsed.port or 3306
    except ValueError:
        host, port = None, 3306

    dbname = parsed.path.lstrip("/") if host else ""
    if not host or not dbname:
        raise RuntimeError(
            f"URL de base inválida: {url!r}. "
            "Esperado host:puerto/base (ej. mysql://host:3306/payments_db)."
        )
    return host, port, dbname


@lru_cache(maxsize=None)
def _load_secret_values(secret_name: str) -> dict:
    """Lee un secret de AWS Secrets Manager y devuelve su JSON como dict.

    Cacheado: un solo GetSecretValue por secret_name por proceso (varias
    conexiones en un mismo run no repiten la llamada a AWS).
    """
    import boto3

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def load(cls) -> "DBConfig":
        """Resuelve la config según el entorno.

        En Lambda/Batch (variables AWS presentes) lee Secrets Manager;
        en local lee variables de entorno / .env.
        """
        in_aws = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("AWS_BATCH_JOB_ID")
        if in_aws:
            return cls.from_secrets_manager()
        return cls.from_env()

    @classmethod
    def from_env(cls) -> "DBConfig":
        missing = [k for k in ("DB_NAME", "DB_USER") if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                f"Faltan variables de entorno: {', '.join(missing)}. "
                "Editá .env en la raíz del repo o exportalas en tu shell."
            )
        return cls(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "3306")),
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ.get("DB_PASSWORD", ""),
        )

    @classmethod
    def from_secrets_manager(cls, secret_name: str | None = None) -> "DBConfig":
        """Construye la config leyendo el secret de Payments en Secrets Manager.

        secret_name: nombre/ARN del secret. Si es None, se toma de PAYMENTS_SECRET_NAME.
        """
        name = secret_name or os.environ.get("PAYMENTS_SECRET_NAME")
        if not name:
            raise RuntimeError(
                "Falta PAYMENTS_SECRET_NAME: no se puede leer el secret de la base "
                "en Secrets Manager."
            )

        values = _load_secret_values(name)
        missing = [
            k for k in (_SECRET_KEY_URL, _SECRET_KEY_USER, _SECRET_KEY_PASSWORD)
            if k not in values
        ]
        if missing:
            raise RuntimeError(
                f"El secret {name!r} no tiene las claves requeridas: {missing}."
            )

        host, port, dbname = _parse_db_url(values[_SECRET_KEY_URL])
        return cls(
            host=host,
            port=port,
            dbname=dbname,
            user=values[_SECRET_KEY_USER],
            password=values[_SECRET_KEY_PASSWORD],
        )


@dataclass(frozen=True)
class RunConfig:
    company_id: int
    mode: str  # "join" | "cascade"
    partial_payment_counts: bool
    calculation_date: date
    grace_days: int = 1      # días calendario de gracia después del vencimiento
    paid_threshold: float = 1.0  # fracción mínima pagada para considerar cuota al día (ej. 0.8 = 80%)
