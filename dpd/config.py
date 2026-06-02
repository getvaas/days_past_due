"""Runtime config for the DPD job.

DB credentials come from env vars (auto-loaded from .env in the repo root);
calculation parameters come from the CLI (see main.py) and are passed around
as a dataclass.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path


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


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str

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


@dataclass(frozen=True)
class RunConfig:
    # company_id (numérico) filtra payment_tape.company_id;
    # company_code (string) filtra scheduled_payments_installments.company_code.
    # No siempre coinciden — ej. sistecredito = 86 en payment_tape, "sistecredito" en installments.
    company_id: int
    company_code: str
    mode: str  # "join" | "cascade"
    partial_payment_counts: bool
    calculation_date: date
    grace_days: int = 1  # días calendario de gracia después del vencimiento
