r"""Ejecutor de DPD sobre archivos Excel (sin MySQL).

Punto de entrada alternativo al job de BD para cuando los datos
llegan como archivos planos. Sirve tanto como módulo importable
como script ejecutable directamente.

Uso como script:
    python -m dpd.excel_runner \
        --schedule tests/Days\ Past\ Due.xlsx \
        --payment-tape tests/Days\ Past\ Due.xlsx \
        --date 2026-10-03 \
        --mode cascade \
        --out resultado_dpd.xlsx

Uso como módulo:
    from dpd.excel_runner import run_from_excel
    detail, summary = run_from_excel(
        schedule_path="...",
        payment_tape_path="...",
        calc_date=date(2026, 10, 3),
    )
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import pandas as pd

from .config import RunConfig
from .modes import cascade_fifo, join_installment

# ─── Constantes ─────────────────────────────────────────────────────────────

BUCKET_COLS = [
    "principal_amount", "interest_amount",
    "guarantee_amount", "tax_amount", "fee_amount",
]

SCHEDULE_SHEET_FALLBACKS = [
    "scheduled_payments_installments", "schedule", "Schedule", "SPI",
]

PT_SHEET_FALLBACKS = [
    "Payment_Tape", "payment_tape", "PT", "payments",
]


# ─── Carga y sanitización ────────────────────────────────────────────────────

def _load_sheet(path: str, sheet_name: Optional[str], fallbacks: list[str]) -> pd.DataFrame:
    """Carga una hoja de Excel por nombre exacto, fallback o primera hoja."""
    xls = pd.ExcelFile(path)
    if sheet_name and sheet_name in xls.sheet_names:
        return pd.read_excel(xls, sheet_name=sheet_name)
    for fb in fallbacks:
        if fb in xls.sheet_names:
            return pd.read_excel(xls, sheet_name=fb)
    return pd.read_excel(xls, sheet_name=xls.sheet_names[0])


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
    path: str,
    sheet_name: Optional[str] = None,
) -> pd.DataFrame:
    """Carga la hoja de scheduled_payments_installments desde Excel y la sanitiza."""
    return sanitize_schedule(_load_sheet(path, sheet_name, SCHEDULE_SHEET_FALLBACKS))


def sanitize_payment_tape(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitiza un DataFrame crudo de Payment_Tape.

    Mismo tratamiento sin importar el origen (Excel o MySQL):
    - Convierte payment_date a datetime.date
    - Normaliza borrower_installment_reference a str
    - Intenta rescatar la referencia de cuota desde columnas Unnamed (solo Excel)
    """
    df = df.copy()
    df["payment_date"] = pd.to_datetime(df["payment_date"], errors="coerce").dt.date

    if (
        "borrower_installment_reference" in df.columns
        and df["borrower_installment_reference"].isna().all()
    ):
        fallback_col = next(
            (c for c in df.columns if c.startswith("Unnamed:") and df[c].notna().any()),
            None,
        )
        if fallback_col:
            print(
                f"⚠  payment_tape.borrower_installment_reference vacía — "
                f"usando columna '{fallback_col}' como referencia de cuota."
            )
            df["borrower_installment_reference"] = df[fallback_col]

    df["borrower_installment_reference"] = _ref_to_str(df["borrower_installment_reference"])
    return df


def load_payment_tape(
    path: str,
    sheet_name: Optional[str] = None,
) -> pd.DataFrame:
    """Carga la hoja de Payment_Tape desde Excel y la sanitiza."""
    return sanitize_payment_tape(_load_sheet(path, sheet_name, PT_SHEET_FALLBACKS))


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

def run_from_excel(
    schedule_path: str,
    payment_tape_path: str,
    calc_date: date,
    mode: str = "cascade",
    grace_days: int = 1,
    partial_counts: bool = False,
    schedule_sheet: Optional[str] = None,
    payment_tape_sheet: Optional[str] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carga los Excel, corre DPD en ambos modos y devuelve (detail_df, summary_df).

    Args:
        schedule_path:      Ruta al Excel con scheduled_payments_installments.
        payment_tape_path:  Ruta al Excel con Payment_Tape (puede ser el mismo archivo).
        calc_date:          Fecha de corte del cálculo.
        mode:               "cascade" | "join" | "both" (default: "cascade").
        grace_days:         Días calendario de gracia tras el vencimiento (default: 1).
        partial_counts:     En cascade, si un pago parcial cuenta como cuota pagada.
        schedule_sheet:     Nombre exacto de la hoja en schedule_path (None = autodetect).
        payment_tape_sheet: Nombre exacto de la hoja en payment_tape_path (None = autodetect).

    Returns:
        detail_df:  Una fila por cuota con columnas CASCADE_DPD, CASCADE_ARREARS,
                    JOIN_DPD, JOIN_ARREARS (y MAX_* por contrato).
        summary_df: Una fila por contrato con DPD máximo y arrears totales.
    """
    print(f"Cargando schedule: {schedule_path}")
    sched_df = load_schedule(schedule_path, schedule_sheet)
    print(f"  → {len(sched_df)} cuotas | {sched_df['borrower_contract_id'].nunique()} contratos")

    print(f"Cargando payment tape: {payment_tape_path}")
    pay_df = load_payment_tape(payment_tape_path, payment_tape_sheet)
    print(f"  → {len(pay_df)} pagos | {pay_df['borrower_contract_id'].nunique()} contratos")

    return compute_dpd(
        sched_df, pay_df, calc_date,
        mode=mode, grace_days=grace_days, partial_counts=partial_counts,
    )


def compute_dpd(
    sched_df: pd.DataFrame,
    pay_df: pd.DataFrame,
    calc_date: date,
    mode: str = "cascade",
    grace_days: int = 1,
    partial_counts: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corre DPD sobre DataFrames ya sanitizados y devuelve (detail_df, summary_df).

    Núcleo de cálculo compartido entre el origen Excel (run_from_excel) y el
    origen MySQL (dpd.integrations.db_excel_runner). No lee archivos ni la BD.
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


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Calcula DPD desde archivos Excel (sin MySQL)."
    )
    p.add_argument("--schedule", required=True, help="Ruta al Excel de scheduled_payments_installments.")
    p.add_argument("--payment-tape", required=True, help="Ruta al Excel de Payment_Tape.")
    p.add_argument(
        "--date", dest="calc_date", type=_parse_date, default=date.today(),
        help="Fecha de corte (YYYY-MM-DD). Default: hoy.",
    )
    p.add_argument(
        "--mode", choices=("cascade", "join", "both"), default="cascade",
        help="Modo de cálculo. Default: cascade.",
    )
    p.add_argument(
        "--grace-days", type=int, default=1,
        help="Días calendario de gracia. Default: 1.",
    )
    p.add_argument(
        "--partial-counts", action="store_true",
        help="En cascade, pago parcial cuenta como cuota pagada.",
    )
    p.add_argument(
        "--schedule-sheet", default=None,
        help="Nombre exacto de la hoja de schedule (autodetect si se omite).",
    )
    p.add_argument(
        "--pt-sheet", default=None,
        help="Nombre exacto de la hoja de payment tape (autodetect si se omite).",
    )
    p.add_argument(
        "--out", default="resultado_dpd.xlsx",
        help="Ruta del Excel de salida. Default: resultado_dpd.xlsx.",
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    detail, summary = run_from_excel(
        schedule_path=args.schedule,
        payment_tape_path=args.payment_tape,
        calc_date=args.calc_date,
        mode=args.mode,
        grace_days=args.grace_days,
        partial_counts=args.partial_counts,
        schedule_sheet=args.schedule_sheet,
        payment_tape_sheet=args.pt_sheet,
    )
    export_results(detail, summary, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
