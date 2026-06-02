"""DPD job entry point — integración MySQL.

scheduled_payments_installments.company_code (string) y payment_tape.company_id
(numérico) no siempre coinciden, así que ambos son flags obligatorios.

Examples:
    python -m dpd.integrations.mysql_runner --company-id 42 --company-code 42 --mode join
    python -m dpd.integrations.mysql_runner --company-id 86 --company-code sistecredito --mode cascade
    python -m dpd.integrations.mysql_runner --company-id 86 --company-code sistecredito --mode cascade --date 2026-04-30
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, datetime

from . import queries
from .db import connect, cursor
from .migrations import ensure_dpd_columns
from .updater import apply_results
from ..config import DBConfig, RunConfig
from ..modes import cascade_fifo, join_installment

log = logging.getLogger("dpd")


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_args(argv: list[str]) -> RunConfig:
    p = argparse.ArgumentParser(description="Compute Days Past Due for a company.")
    p.add_argument(
        "--company-id",
        type=int,
        required=True,
        help="company_id numérico para filtrar payment_tape (ej. 86).",
    )
    p.add_argument(
        "--company-code",
        type=str,
        required=True,
        help="company_code para filtrar scheduled_payments_installments (ej. 'sistecredito').",
    )
    p.add_argument("--mode", choices=("join", "cascade"), required=True)
    p.add_argument(
        "--partial-counts",
        action="store_true",
        help="Si se incluye, un pago parcial cuenta como cuota pagada (modo cascade).",
    )
    p.add_argument(
        "--date",
        dest="calculation_date",
        type=_parse_date,
        default=date.today(),
        help="Fecha de cálculo (YYYY-MM-DD). Default: hoy.",
    )
    p.add_argument(
        "--print-summary",
        action="store_true",
        help="Imprime DPD por contrato al final.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe ni corre migraciones. Solo calcula y muestra una preview.",
    )
    p.add_argument(
        "--check-connection",
        action="store_true",
        help="Solo prueba conexión y cuenta filas para el company_id; sale.",
    )
    p.add_argument(
        "--grace-days",
        type=int,
        default=1,
        help="Días calendario de gracia tras el vencimiento antes de contar mora. Default: 1.",
    )
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    return (
        RunConfig(
            company_id=args.company_id,
            company_code=args.company_code,
            mode=args.mode,
            partial_payment_counts=args.partial_counts,
            calculation_date=args.calculation_date,
            grace_days=args.grace_days,
        ),
        args.print_summary,
        args.dry_run,
        args.check_connection,
    )


def _check_connection(conn, company_id: int, company_code: str) -> None:
    with cursor(conn) as cur:
        cur.execute("SELECT DATABASE() AS db, CURRENT_USER() AS usr, VERSION() AS ver;")
        info = cur.fetchone()
        log.info("Conectado: db=%s user=%s", info["db"], info["usr"])
        log.info("Server: %s", info["ver"])

        cur.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME IN ('scheduled_payments_installments', 'payment_tape');"
        )
        tables = {row["TABLE_NAME"] for row in cur.fetchall()}
        log.info(
            "Tablas: scheduled_payments_installments=%s payment_tape=%s",
            "OK" if "scheduled_payments_installments" in tables else "MISSING",
            "OK" if "payment_tape" in tables else "MISSING",
        )
        if not {"scheduled_payments_installments", "payment_tape"}.issubset(tables):
            log.error("Falta alguna tabla en la BD actual (%s).", info["db"])
            return

        cur.execute(
            "SELECT COUNT(*) AS n FROM scheduled_payments_installments WHERE company_code = %s;",
            (company_code,),
        )
        log.info(
            "scheduled_payments_installments para company_code=%s: %s filas",
            company_code, cur.fetchone()["n"],
        )

        cur.execute(
            "SELECT COUNT(*) AS n FROM payment_tape WHERE company_id = %s;",
            (company_id,),
        )
        log.info(
            "payment_tape para company_id=%s: %s filas",
            company_id, cur.fetchone()["n"],
        )


def run(
    cfg: RunConfig,
    print_summary: bool = False,
    dry_run: bool = False,
    check_only: bool = False,
) -> int:
    db_cfg = DBConfig.from_env()
    started = time.monotonic()

    conn = connect(db_cfg)
    try:
        if check_only:
            _check_connection(conn, cfg.company_id, cfg.company_code)
            return 0

        if dry_run:
            log.warning("DRY RUN: no se corre ALTER TABLE ni se escribe a la BD")
        else:
            ensure_dpd_columns(conn)

        if cfg.mode == "join":
            results = join_installment.compute(conn, cfg)
        elif cfg.mode == "cascade":
            results = cascade_fifo.compute(conn, cfg)
        else:
            raise ValueError(f"Unknown mode: {cfg.mode}")

        if dry_run:
            preview = list(results)
            non_zero = [r for r in preview if r["dpd_current"] > 0]
            log.info("DRY RUN: %d cuotas calculadas, %d con dpd_current>0", len(preview), len(non_zero))
            for r in non_zero[:20]:
                log.info("  id=%s dpd=%s arrears=%s", r["id"], r["dpd_current"], r["amount_in_arrears"])
            if len(non_zero) > 20:
                log.info("  ... %d filas más en mora", len(non_zero) - 20)
            return len(preview)

        rows_written = apply_results(conn, results)

        log.info(
            "Done. company_id=%s company_code=%s mode=%s partial_counts=%s date=%s rows=%d elapsed=%.2fs",
            cfg.company_id, cfg.company_code, cfg.mode, cfg.partial_payment_counts,
            cfg.calculation_date, rows_written, time.monotonic() - started,
        )

        if print_summary:
            current = queries.current_dpd_by_contract(conn, cfg.company_code)
            log.info("DPD actual por contrato (%d filas):", len(current))
            for row in current:
                log.info("  %s -> %s", row["borrower_contract_id"], row["dpd_credito"])

            historic = queries.max_dpd_by_contract(conn, cfg.company_code)
            log.info("DPD máximo histórico por contrato (%d filas):", len(historic))
            for row in historic:
                log.info("  %s -> %s", row["borrower_contract_id"], row["max_tiempo_mora"])

        return rows_written
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    cfg, print_summary, dry_run, check_only = _parse_args(
        argv if argv is not None else sys.argv[1:]
    )
    run(cfg, print_summary=print_summary, dry_run=dry_run, check_only=check_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
