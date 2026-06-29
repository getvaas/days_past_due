"""Lectura de payments_db (solo lectura) para el flujo de cálculo.

Dos responsabilidades:
- `load_schedule` / `load_payment_tape`: leen las tablas de cálculo
  (scheduled_payments_installments / payment_tape) filtradas por compañía, las
  sanitizan y devuelven **polars DataFrames** listos para los productos.
- `read_last_dates`: fechas máximas (last_*) para poblar el mensaje de respuesta.

No escribe nada a la BD. Requiere acceso al host MySQL (credenciales resueltas por
DBConfig.load()).
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import polars as pl

from .config import DBConfig
from .integrations.db import connection
from .utils.dates import to_date as _to_date


# ─── SQL ──────────────────────────────────────────────────────────────────────
# SELECT * por portabilidad: prod trae más columnas que el esquema de prueba y el
# sanitizador toma solo las necesarias. Solo lectura.
SCHEDULE_SQL = """
SELECT *
FROM scheduled_payments_installments
WHERE company_id = %(company_id)s
ORDER BY borrower_contract_id, `date` ASC, id ASC;
"""

PAYMENT_TAPE_SQL = """
SELECT *
FROM payment_tape
WHERE company_id = %(company_id)s
  AND payment_date IS NOT NULL
ORDER BY borrower_contract_id, payment_date ASC, id ASC;
"""

SPI_LAST_DATE_SQL = """
SELECT MAX(`date`) AS last_schedule_payment_date
FROM scheduled_payments_installments
WHERE company_id = %(company_id)s;
"""

PAYMENTS_LAST_DATE_SQL = """
SELECT MAX(payment_date) AS last_payment_tape_date
FROM payment_tape
WHERE company_id = %(company_id)s;
"""

PAYMENTS_LAST_PAYMENT_SQL = """
SELECT MAX(payment_date) AS last_payment_date
FROM payment_tape
WHERE company_id = %(company_id)s
  AND total_payment > 0;
"""


# ─── Constantes ───────────────────────────────────────────────────────────────
BUCKET_COLS = [
    "principal_amount", "interest_amount",
    "guarantee_amount", "tax_amount", "fee_amount",
]

# Columnas mínimas de payment_tape para construir un DataFrame vacío bien formado
# cuando la compañía no tiene pagos.
_PT_MIN_COLS = [
    "borrower_contract_id", "borrower_installment_reference",
    "payment_date", "total_payment",
]
_PT_EMPTY_SCHEMA = {
    "borrower_contract_id": pl.Utf8,
    "borrower_installment_reference": pl.Utf8,
    "payment_date": pl.Date,
    "total_payment": pl.Float64,
}


# ─── Helpers de sanitización (polars) ─────────────────────────────────────────

def _to_date_expr(col: str, dtype: pl.DataType) -> pl.Expr:
    """Coacciona una columna a pl.Date sin importar el origen (str ISO, Datetime, Date)."""
    if dtype == pl.Date:
        return pl.col(col)
    if dtype == pl.Datetime:
        return pl.col(col).dt.date()
    return pl.col(col).cast(pl.Utf8).str.to_date(strict=False)


def _ref_to_str_expr(col: str, dtype: pl.DataType) -> pl.Expr:
    """Normaliza borrower_installment_reference a string (maneja floats de Excel)."""
    if dtype in (pl.Float32, pl.Float64):
        return pl.col(col).cast(pl.Int64).cast(pl.Utf8)
    return pl.col(col).cast(pl.Utf8)


def _sanitize_schedule(df: pl.DataFrame) -> pl.DataFrame:
    """Sanitiza scheduled_payments_installments crudo (mismo trato venga de donde venga):
    convierte `date` a date, normaliza la referencia a str, asigna id sintético si
    falta, y rellena buckets vacíos con gross_amount → principal_amount.
    """
    df = df.with_columns(_to_date_expr("date", df["date"].dtype).alias("date"))
    df = df.with_columns(
        _ref_to_str_expr("borrower_installment_reference",
                         df["borrower_installment_reference"].dtype)
        .alias("borrower_installment_reference")
    )

    if "id" not in df.columns:
        df = df.with_row_index(name="id", offset=1)

    for col in BUCKET_COLS:
        if col not in df.columns:
            df = df.with_columns(pl.lit(0).alias(col))
    df = df.with_columns([pl.col(c).fill_null(0) for c in BUCKET_COLS])

    # Fallback: cuota sin desglose de buckets → principal_amount = gross_amount.
    bucket_sum = pl.sum_horizontal([pl.col(c) for c in BUCKET_COLS])
    df = df.with_columns(
        pl.when((bucket_sum == 0) & (pl.col("gross_amount").fill_null(0) > 0))
        .then(pl.col("gross_amount"))
        .otherwise(pl.col("principal_amount"))
        .alias("principal_amount")
    )
    return df


def _sanitize_payment_tape(df: pl.DataFrame) -> pl.DataFrame:
    """Sanitiza payment_tape crudo: payment_date a date y referencia a str."""
    df = df.with_columns(_to_date_expr("payment_date", df["payment_date"].dtype).alias("payment_date"))
    df = df.with_columns(
        _ref_to_str_expr("borrower_installment_reference",
                         df["borrower_installment_reference"].dtype)
        .alias("borrower_installment_reference")
    )
    return df


# ─── Acceso a BD ──────────────────────────────────────────────────────────────

def _fetchall(sql: str, params: dict, db_cfg: Optional[DBConfig] = None) -> list[dict]:
    """Ejecuta una query de solo lectura y devuelve todas las filas (lista de dicts)."""
    cfg = db_cfg or DBConfig.load()
    with connection(cfg) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def load_schedule(company_id: int, db_cfg: Optional[DBConfig] = None) -> pl.DataFrame:
    """Lee scheduled_payments_installments (filtrada por company_id) y la sanitiza.

    Devuelve un DataFrame vacío si la compañía no tiene cuotas.
    """
    rows = _fetchall(SCHEDULE_SQL, {"company_id": int(company_id)}, db_cfg)
    if not rows:
        return pl.DataFrame()
    return _sanitize_schedule(pl.DataFrame(rows))


def load_payment_tape(company_id: int, db_cfg: Optional[DBConfig] = None) -> pl.DataFrame:
    """Lee payment_tape (filtrada por company_id) y la sanitiza.

    Si la compañía no tiene pagos, devuelve un DataFrame vacío con las columnas
    mínimas (el cálculo lo interpreta como "todo en mora").
    """
    rows = _fetchall(PAYMENT_TAPE_SQL, {"company_id": int(company_id)}, db_cfg)
    if not rows:
        return pl.DataFrame(schema=_PT_EMPTY_SCHEMA)
    return _sanitize_payment_tape(pl.DataFrame(rows))


def read_last_dates(
    company_id: int,
    db_cfg: Optional[DBConfig] = None,
) -> dict[str, Optional[date]]:
    """Devuelve las fechas más recientes de cada fuente de datos.

    Usado para poblar metadata.last_* en el mensaje de respuesta.
    """
    cfg = db_cfg or DBConfig.load()
    with connection(cfg) as cur:
        cur.execute(SPI_LAST_DATE_SQL, {"company_id": company_id})
        spi_row = cur.fetchone()

        cur.execute(PAYMENTS_LAST_DATE_SQL, {"company_id": company_id})
        pt_row = cur.fetchone()

        cur.execute(PAYMENTS_LAST_PAYMENT_SQL, {"company_id": company_id})
        pay_row = cur.fetchone()

    return {
        "last_schedule_payment_date": _to_date(spi_row["last_schedule_payment_date"] if spi_row else None),
        "last_payment_tape_date": _to_date(pt_row["last_payment_tape_date"] if pt_row else None),
        "last_payment_date": _to_date(pay_row["last_payment_date"] if pay_row else None),
    }
