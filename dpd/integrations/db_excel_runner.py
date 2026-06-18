"""Lee schedule + payment_tape desde MySQL (SOLO LECTURA) y exporta DPD a Excel.

A diferencia de dpd.integrations.mysql_runner, este módulo NO escribe en la base
de datos: no corre migraciones ni updater, solo hace SELECT. Reutiliza el mismo
núcleo de cálculo del runner de Excel (dpd.excel_runner.compute_dpd) y exporta el
resultado al mismo formato de archivo.

Pensado para el análisis del día anterior de una compañía:
    company_id   (numérico) filtra payment_tape.company_id
    company_code (string)   filtra scheduled_payments_installments.company_code

Uso como script (pregunta company_id/company_code si no se pasan):
    python -m dpd.integrations.db_excel_runner
    python -m dpd.integrations.db_excel_runner --company-id 86 --company-code sistecredito
    python -m dpd.integrations.db_excel_runner --company-id 86 --company-code sistecredito --date 2026-06-01

Uso como módulo:
    from dpd.integrations.db_excel_runner import run_from_db
    detail, summary, sched_df, pay_df = run_from_db(company_id=86, company_code="sistecredito")
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

from ..config import DBConfig
from ..excel_runner import compute_dpd, export_results, load_payment_tape, load_schedule

# Nombre de la base por defecto (pedido del cliente). Se puede pisar con --dbname
# o con DB_NAME en el .env.
DEFAULT_DBNAME = "payments_db"


def yesterday() -> date:
    """Fecha del día anterior — corte por defecto del análisis."""
    return date.today() - timedelta(days=1)


def _db_config(dbname: Optional[str] = None) -> DBConfig:
    cfg = DBConfig.from_env()
    target = dbname or cfg.dbname or DEFAULT_DBNAME
    if target == cfg.dbname:
        return cfg
    return DBConfig(
        host=cfg.host, port=cfg.port, dbname=target,
        user=cfg.user, password=cfg.password,
    )


def run_from_db(
    company_id: int,
    company_code: str,
    calc_date: Optional[date] = None,
    mode: str = "both",
    grace_days: int = 1,
    partial_counts: bool = False,
    dbname: Optional[str] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Lee ambas tablas de payments_db (solo lectura) vía los loaders canónicos y calcula DPD.

    Returns (detail_df, summary_df, sched_df, pay_df). calc_date None = ayer.
    """
    calc_date = calc_date or yesterday()
    cfg = _db_config(dbname)
    print(f"Conectando (solo lectura): {cfg.user}@{cfg.host}:{cfg.port}/{cfg.dbname}")
    print(f"Corte: {calc_date} (día anterior) | company_id={company_id} | company_code={company_code!r}")

    sched_df = load_schedule(company_code, db_cfg=cfg)
    if sched_df.empty:
        raise SystemExit(
            f"No hay filas en scheduled_payments_installments para "
            f"company_code={company_code!r}. Revisá el valor."
        )
    print(f"  schedule:     {len(sched_df)} cuotas | {sched_df['borrower_contract_id'].nunique()} contratos")

    pay_df = load_payment_tape(company_id, db_cfg=cfg)
    if pay_df.empty:
        print(f"⚠  payment_tape sin pagos para company_id={company_id} — todo quedará en mora.")
    print(f"  payment_tape: {len(pay_df)} pagos")

    result_df, summary_df = compute_dpd(
        sched_df, pay_df, calc_date,
        mode=mode, grace_days=grace_days, partial_counts=partial_counts,
    )
    return result_df, summary_df, sched_df, pay_df


# ─── Prompts interactivos ─────────────────────────────────────────────────────

def prompt_company_id(value: Optional[int] = None) -> int:
    """Pregunta el company_id (numérico) si no vino por argumento."""
    while value is None:
        raw = input("¿Qué company_id vas a revisar? (numérico, para payment_tape): ").strip()
        try:
            value = int(raw)
        except ValueError:
            print("  → tiene que ser un número entero. Probá de nuevo.")
    return value


def prompt_company_code(value: Optional[str] = None) -> str:
    """Pregunta el company_code (string) si no vino por argumento."""
    while not value:
        value = input(
            "company_code (string, para scheduled_payments_installments): "
        ).strip()
    return value


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Lee DPD desde MySQL (solo lectura) y exporta a Excel."
    )
    p.add_argument("--company-id", type=int, default=None,
                   help="company_id numérico (payment_tape). Si se omite, se pregunta.")
    p.add_argument("--company-code", type=str, default=None,
                   help="company_code string (installments). Si se omite, se pregunta.")
    p.add_argument("--date", dest="calc_date", type=_parse_date, default=None,
                   help="Fecha de corte (YYYY-MM-DD). Default: ayer.")
    p.add_argument("--mode", choices=("cascade", "join", "both"), default="both",
                   help="Modo de cálculo. Default: both.")
    p.add_argument("--grace-days", type=int, default=1,
                   help="Días calendario de gracia. Default: 1.")
    p.add_argument("--partial-counts", action="store_true",
                   help="En cascade, pago parcial cuenta como cuota pagada.")
    p.add_argument("--dbname", default=None,
                   help=f"Nombre de la base. Default: DB_NAME del .env o '{DEFAULT_DBNAME}'.")
    p.add_argument("--out", default="resultado_dpd.xlsx",
                   help="Ruta del Excel de salida. Default: resultado_dpd.xlsx.")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    company_id = prompt_company_id(args.company_id)
    company_code = prompt_company_code(args.company_code)

    detail, summary, _sched, _pay = run_from_db(
        company_id=company_id,
        company_code=company_code,
        calc_date=args.calc_date,
        mode=args.mode,
        grace_days=args.grace_days,
        partial_counts=args.partial_counts,
        dbname=args.dbname,
    )
    export_results(detail, summary, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
