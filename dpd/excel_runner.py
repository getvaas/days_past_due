"""Carga de datos de cálculo desde payments_db y núcleo de cómputo DPD.

`load_schedule`/`load_payment_tape` leen las tablas de payments_db (filtradas por
compañía) y las sanitizan; `compute_dpd` corre el cálculo sobre los DataFrames ya
sanitizados. La entrada es siempre la base de datos — ya no se leen archivos planos.

Uso como módulo:
    from dpd.excel_runner import load_schedule, load_payment_tape, compute_dpd
    sched = load_schedule(company_code="sistecredito")
    pays = load_payment_tape(company_id=86)
    detail, summary = compute_dpd(sched, pays, calc_date=date(2026, 10, 3))
"""
from __future__ import annotations

import os
from datetime import date
from typing import Optional

import pandas as pd

from .config import DBConfig, RunConfig
from .integrations.db import connect, cursor
from .modes import cascade_fifo, join_installment

# ─── Constantes ─────────────────────────────────────────────────────────────

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

# SELECT * por portabilidad: prod trae más columnas que el esquema de prueba y el
# sanitizador toma solo las necesarias. Solo lectura.
SCHEDULE_SQL = """
SELECT *
FROM scheduled_payments_installments
WHERE company_code = %(company_code)s
ORDER BY borrower_contract_id, `date` ASC, id ASC;
"""

PAYMENT_TAPE_SQL = """
SELECT *
FROM payment_tape
WHERE company_id = %(company_id)s
  AND payment_date IS NOT NULL
ORDER BY borrower_contract_id, payment_date ASC, id ASC;
"""


# ─── Sanitización ────────────────────────────────────────────────────────────

def _ref_to_str(s: pd.Series) -> pd.Series:
    """Normaliza borrower_installment_reference a string (maneja floats de Excel)."""
    if pd.api.types.is_float_dtype(s):
        return s.where(s.isna(), s.astype("Int64")).astype(str)
    return s.astype(str)


def sanitize_schedule(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitiza un DataFrame crudo de scheduled_payments_installments.

    Mismo tratamiento sin importar el origen (Excel o MySQL):
    - Convierte `date` a datetime.date
    - Normaliza borrower_installment_reference a str
    - Asigna id sintético si no viene
    - Rellena buckets vacíos con gross_amount → principal_amount
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["borrower_installment_reference"] = _ref_to_str(df["borrower_installment_reference"])

    df = df.reset_index(drop=True)
    if "id" not in df.columns or df["id"].isna().all():
        df["id"] = df.index + 1
    else:
        df["id"] = df["id"].fillna(pd.Series(df.index + 1, index=df.index)).astype(int)

    for col in BUCKET_COLS:
        if col not in df.columns:
            df[col] = 0
    df[BUCKET_COLS] = df[BUCKET_COLS].fillna(0)

    bucket_sum = df[BUCKET_COLS].sum(axis=1)
    need_fallback = (bucket_sum == 0) & (df["gross_amount"].fillna(0) > 0)
    n_filled = int(need_fallback.sum())
    if n_filled > 0:
        df.loc[need_fallback, "principal_amount"] = df.loc[need_fallback, "gross_amount"]
        print(f"⚠  {n_filled} cuota(s) sin desglose de buckets → principal_amount = gross_amount")

    return df


def load_schedule(
    company_code: str,
    db_cfg: Optional[DBConfig] = None,
) -> pd.DataFrame:
    """Lee scheduled_payments_installments de payments_db (filtrada por company_code) y la sanitiza.

    Devuelve un DataFrame vacío si la compañía no tiene cuotas (el caller decide
    qué hacer, p.ej. generar el SPI).
    """
    cfg = db_cfg or DBConfig.load()
    conn = connect(cfg)
    try:
        with cursor(conn) as cur:
            cur.execute(SCHEDULE_SQL, {"company_code": str(company_code)})
            rows = cur.fetchall()
    finally:
        conn.close()

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return sanitize_schedule(df)


def sanitize_payment_tape(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitiza un DataFrame crudo de payment_tape (desde payments_db).

    - Convierte payment_date a datetime.date
    - Normaliza borrower_installment_reference a str
    """
    df = df.copy()
    df["payment_date"] = pd.to_datetime(df["payment_date"], errors="coerce").dt.date
    df["borrower_installment_reference"] = _ref_to_str(df["borrower_installment_reference"])
    return df


def load_payment_tape(
    company_id: int,
    db_cfg: Optional[DBConfig] = None,
) -> pd.DataFrame:
    """Lee payment_tape de payments_db (filtrada por company_id) y la sanitiza.

    Si la compañía no tiene pagos, devuelve un DataFrame vacío con las columnas
    mínimas (el cálculo lo interpreta como "todo en mora").
    """
    cfg = db_cfg or DBConfig.load()
    conn = connect(cfg)
    try:
        with cursor(conn) as cur:
            cur.execute(PAYMENT_TAPE_SQL, {"company_id": company_id})
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return pd.DataFrame(columns=_PT_MIN_COLS)
    return sanitize_payment_tape(pd.DataFrame(rows))


# ─── Conversión a dicts para los modos ───────────────────────────────────────

def _installments_from_df(df: pd.DataFrame) -> list[dict]:
    """Convierte schedule DataFrame a lista de dicts para compute_from_data().
    Descarta filas con date NaT o gross_amount inválido.
    Acepta tanto 'date' como 'installment_date' como nombre de columna de fecha.
    """
    date_col = "installment_date" if "installment_date" in df.columns else "date"
    valid = df[df[date_col].notna() & (df["gross_amount"].fillna(0) > 0)]
    return [
        {
            "id": int(r["id"]),
            "borrower_contract_id": r["borrower_contract_id"],
            "borrower_installment_reference": r["borrower_installment_reference"],
            "installment_date": r[date_col],
            "gross_amount": r.get("gross_amount", 0),
            "guarantee_amount": r.get("guarantee_amount", 0),
            "principal_amount": r.get("principal_amount", 0),
            "interest_amount": r.get("interest_amount", 0),
            "tax_amount": r.get("tax_amount", 0),
            "fee_amount": r.get("fee_amount", 0),
        }
        for _, r in valid.iterrows()
    ]


def _payments_from_df(df: pd.DataFrame) -> list[dict]:
    """Convierte payment_tape DataFrame a lista de dicts para compute_from_data().
    Descarta filas con payment_date NaT o total_payment <= 0."""
    valid = df[df["payment_date"].notna() & (df["total_payment"].fillna(0) > 0)]
    return [
        {
            "borrower_contract_id": r["borrower_contract_id"],
            "borrower_installment_reference": r.get("borrower_installment_reference"),
            "payment_date": r["payment_date"],
            "total_payment": r.get("total_payment", 0),
        }
        for _, r in valid.iterrows()
    ]


# ─── Cómputo principal ────────────────────────────────────────────────────────

def compute_dpd(
    sched_df: pd.DataFrame,
    pay_df: pd.DataFrame,
    calc_date: date,
    mode: str = "cascade",
    grace_days: int = 1,
    partial_counts: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corre DPD sobre DataFrames ya sanitizados y devuelve (detail_df, summary_df).

    Núcleo de cálculo compartido. Opera sobre DataFrames ya sanitizados
    (ver load_schedule / load_payment_tape). No lee la BD por sí mismo.
    """
    insts = _installments_from_df(sched_df)
    pays = _payments_from_df(pay_df)

    cfg_base = dict(
        company_id=0,
        company_code="*",
        partial_payment_counts=partial_counts,
        calculation_date=calc_date,
        grace_days=grace_days,
    )

    run_cascade = mode in ("cascade", "both")
    run_join = mode in ("join", "both")

    result_df = sched_df.copy()

    if run_cascade:
        cfg_c = RunConfig(**cfg_base, mode="cascade")
        c_results = list(cascade_fifo.compute_from_data(insts, pays, cfg_c))
        cdf = pd.DataFrame(c_results).rename(columns={
            "dpd_current": "CASCADE_DPD",
            "amount_in_arrears": "CASCADE_ARREARS",
        })
        cdf["CASCADE_ARREARS"] = cdf["CASCADE_ARREARS"].astype(float)
        result_df = result_df.merge(cdf, on="id", how="left")
        result_df.loc[result_df["CASCADE_DPD"] == 0, "CASCADE_ARREARS"] = 0.0
        result_df["MAX_CASCADE_DPD"] = result_df.groupby("borrower_contract_id")["CASCADE_DPD"].transform("max")

    if run_join:
        cfg_j = RunConfig(**cfg_base, mode="join")
        j_results = list(join_installment.compute_from_data(insts, pays, cfg_j))
        jdf = pd.DataFrame(j_results).rename(columns={
            "dpd_current": "JOIN_DPD",
            "amount_in_arrears": "JOIN_ARREARS",
        })
        jdf["JOIN_ARREARS"] = jdf["JOIN_ARREARS"].astype(float)
        result_df = result_df.merge(jdf, on="id", how="left")
        result_df.loc[result_df["JOIN_DPD"] == 0, "JOIN_ARREARS"] = 0.0
        result_df["MAX_JOIN_DPD"] = result_df.groupby("borrower_contract_id")["JOIN_DPD"].transform("max")

    # Resumen por contrato
    agg_cols: dict = {"cuotas": ("id", "count")}
    if run_cascade:
        result_df["_c_arr_ov"] = result_df.where(result_df["CASCADE_DPD"] > 0)["CASCADE_ARREARS"]
        agg_cols["cascade_dpd_max"] = ("CASCADE_DPD", "max")
        agg_cols["cascade_arrears_total"] = ("_c_arr_ov", "sum")
    if run_join:
        result_df["_j_arr_ov"] = result_df.where(result_df["JOIN_DPD"] > 0)["JOIN_ARREARS"]
        agg_cols["join_dpd_max"] = ("JOIN_DPD", "max")
        agg_cols["join_arrears_total"] = ("_j_arr_ov", "sum")

    summary_df = (
        result_df.groupby("borrower_contract_id", as_index=False)
                 .agg(**agg_cols)
                 .sort_values(
                     "cascade_dpd_max" if run_cascade else "join_dpd_max",
                     ascending=False,
                 )
    )

    # Limpiar columnas temporales
    for tmp in ["_c_arr_ov", "_j_arr_ov"]:
        if tmp in result_df.columns:
            result_df = result_df.drop(columns=[tmp])

    dpd_cascade = int((result_df.get("CASCADE_DPD", pd.Series([], dtype=int)) > 0).sum())
    dpd_join = int((result_df.get("JOIN_DPD", pd.Series([], dtype=int)) > 0).sum())
    print(
        f"\nResultado — {len(result_df)} cuotas calculadas | "
        f"grace_days={grace_days} | corte={calc_date}"
    )
    if run_cascade:
        print(f"  CASCADE: {dpd_cascade} cuotas en mora")
    if run_join:
        print(f"  JOIN:    {dpd_join} cuotas en mora")

    return result_df, summary_df


def export_results(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    out_path: str,
) -> None:
    """Exporta detail y summary a un Excel con dos hojas."""
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        detail_df.to_excel(writer, sheet_name="schedule_con_dpd", index=False)
        summary_df.to_excel(writer, sheet_name="resumen_por_contrato", index=False)
    print(f"Exportado: {os.path.abspath(out_path)}")
    print(f"  - schedule_con_dpd:     {len(detail_df)} filas")
    print(f"  - resumen_por_contrato: {len(summary_df)} filas")
