"""SPI Builder — genera scheduled_payments_installments desde el loan tape.

Cuando no existen cuotas en BD para una compañía, este módulo:
1. Lee los campos necesarios del loan tape (por contrato).
2. Convierte la tasa anual efectiva a tasa periódica.
3. Genera el calendario de amortización (PMT, cuota fija).
4. Inserta las cuotas en scheduled_payments_installments (MySQL).
5. Devuelve el DataFrame resultante para que el run continúe sin releer BD.

Solo aplica para rate_type='fixed'. Para rate_type='variable' el SPI
debe cargarse manualmente antes de invocar la Lambda.

Fórmula de conversión de tasa:
    tasa_periódica = (1 + tasa_anual_efectiva) ^ (1 / períodos_por_año) - 1

Fórmula PMT:
    pmt = P * r / (1 - (1 + r)^-n)
    Donde P = principal, r = tasa periódica, n = número de cuotas.

Columnas esperadas en el loan tape (nombres configurables vía LoanTapeColumns):
    borrower_contract_id     — identificador del crédito
    original_principal       — monto original desembolsado
    num_installments         — número de cuotas
    interest_rate            — tasa anual efectiva (ej. 0.24 = 24%)
    first_installment_date   — fecha de la primera cuota (date o str YYYY-MM-DD)
    periodicity              — 'monthly' | 'biweekly' | 'weekly' | 'daily'
                               Si vacío/nulo → se asume 'monthly'
"""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

import pandas as pd

from .config import DBConfig
from .integrations.db import connect, cursor

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Periodicidad
# ---------------------------------------------------------------------------

#: Períodos por año para cada periodicidad.
PERIODS_PER_YEAR: dict[str, int] = {
    "monthly": 12,
    "biweekly": 26,
    "weekly": 52,
    "daily": 365,
}

DEFAULT_PERIODICITY = "monthly"

_PERIODICITY_ALIASES: dict[str, str] = {
    "mensual": "monthly",
    "quincenal": "biweekly",
    "semanal": "weekly",
    "diario": "daily",
    "m": "monthly",
    "b": "biweekly",
    "w": "weekly",
    "d": "daily",
}


def _normalize_periodicity(raw) -> str:
    """Normaliza el valor de periodicidad del loan tape."""
    if raw is None:
        return DEFAULT_PERIODICITY
    if isinstance(raw, float) and raw != raw:  # NaN
        return DEFAULT_PERIODICITY
    s = str(raw).strip().lower()
    if not s:
        return DEFAULT_PERIODICITY
    if s in PERIODS_PER_YEAR:
        return s
    if s in _PERIODICITY_ALIASES:
        return _PERIODICITY_ALIASES[s]
    log.warning("Periodicidad desconocida %r — asumiendo 'monthly'", raw)
    return DEFAULT_PERIODICITY


def _period_rate(annual_effective_rate: Decimal, periodicity: str) -> Decimal:
    """Convierte tasa anual efectiva a tasa periódica.

    Fórmula: (1 + r_anual) ^ (1/n) - 1
    donde n = períodos por año según periodicidad.
    """
    n = PERIODS_PER_YEAR[periodicity]
    r_annual = float(annual_effective_rate)
    r_period = (1 + r_annual) ** (1.0 / n) - 1
    return Decimal(str(r_period))


def _add_months(d: date, months: int) -> date:
    """Suma `months` meses a una fecha, ajustando el día si el mes destino es más corto."""
    if months == 0:
        return d
    total_months = d.month + months
    year = d.year + (total_months - 1) // 12
    month = (total_months - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _installment_date(first: date, periodicity: str, step: int) -> date:
    """Calcula la fecha del installment número (step+1) desde `first`.

    step=0 → primera cuota = first.
    step=1 → segunda cuota = first + 1 período. Etc.
    """
    if step == 0:
        return first
    if periodicity == "monthly":
        return _add_months(first, step)
    elif periodicity == "biweekly":
        return first + timedelta(weeks=2 * step)
    elif periodicity == "weekly":
        return first + timedelta(weeks=step)
    elif periodicity == "daily":
        return first + timedelta(days=step)
    return _add_months(first, step)  # fallback


# ---------------------------------------------------------------------------
# Amortización (PMT, cuota fija)
# ---------------------------------------------------------------------------

@dataclass
class Installment:
    borrower_contract_id: str
    installment_number: int
    installment_date: date
    gross_amount: Decimal
    principal_amount: Decimal
    interest_amount: Decimal


def build_schedule(
    borrower_contract_id: str,
    principal: Decimal,
    annual_rate: Decimal,
    num_installments: int,
    first_installment_date: date,
    periodicity: str = "monthly",
) -> list[Installment]:
    """Genera el calendario de amortización de cuota fija (PMT).

    Para tasa cero divide el principal en partes iguales (capital puro).
    La última cuota absorbe los centavos de redondeo.
    """
    r = _period_rate(annual_rate, periodicity)
    n = num_installments
    TWO_DEC = Decimal("0.01")

    if r == 0:
        pmt = (principal / Decimal(n)).quantize(TWO_DEC, rounding=ROUND_HALF_UP)
    else:
        factor = (1 + float(r)) ** (-n)
        pmt_raw = float(principal) * float(r) / (1 - factor)
        pmt = Decimal(str(pmt_raw)).quantize(TWO_DEC, rounding=ROUND_HALF_UP)

    installments: list[Installment] = []
    balance = principal

    for i in range(1, n + 1):
        inst_date = _installment_date(first_installment_date, periodicity, i - 1)
        interest = (balance * r).quantize(TWO_DEC, rounding=ROUND_HALF_UP)

        if i < n:
            principal_part = (pmt - interest).quantize(TWO_DEC, rounding=ROUND_HALF_UP)
            # Guardar al menos 1 centavo de principal por cuota
            if principal_part <= 0:
                principal_part = Decimal("0.01")
        else:
            # Última cuota: liquida el saldo restante
            principal_part = balance
            pmt = (principal_part + interest).quantize(TWO_DEC, rounding=ROUND_HALF_UP)

        gross = (principal_part + interest).quantize(TWO_DEC, rounding=ROUND_HALF_UP)
        balance = (balance - principal_part).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        if balance < 0:
            balance = Decimal(0)

        installments.append(Installment(
            borrower_contract_id=str(borrower_contract_id),
            installment_number=i,
            installment_date=inst_date,
            gross_amount=gross,
            principal_amount=principal_part,
            interest_amount=interest,
        ))

    return installments


# ---------------------------------------------------------------------------
# Persistencia MySQL
# ---------------------------------------------------------------------------

_INSERT_SQL = """
INSERT INTO scheduled_payments_installments
    (company_id,
     borrower_contract_id,
     borrower_installment_reference,
     `date`,
     gross_amount,
     principal_amount,
     interest_amount,
     guarantee_amount,
     tax_amount,
     fee_amount)
VALUES
    (%(company_id)s,
     %(borrower_contract_id)s,
     %(borrower_installment_reference)s,
     %(date)s,
     %(gross_amount)s,
     %(principal_amount)s,
     %(interest_amount)s,
     0, 0, 0);
"""


def _insert_batch(conn, company_id: int, installments: list[Installment]) -> int:
    """Inserta todas las cuotas en un solo executemany dentro de la conexión abierta."""
    rows = [
        {
            "company_id": company_id,
            "borrower_contract_id": inst.borrower_contract_id,
            "borrower_installment_reference": str(inst.installment_number),
            "date": inst.installment_date,
            "gross_amount": float(inst.gross_amount),
            "principal_amount": float(inst.principal_amount),
            "interest_amount": float(inst.interest_amount),
        }
        for inst in installments
    ]
    with cursor(conn) as cur:
        cur.executemany(_INSERT_SQL, rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Columnas del loan tape (configurables)
# ---------------------------------------------------------------------------

@dataclass
class LoanTapeColumns:
    """Nombres de columnas del loan tape que usa el SPI builder.

    Si los nombres en el loan tape difieren de los defaults, instanciar
    con los nombres reales. Ej.:
        cols = LoanTapeColumns(original_principal="disbursement_amount")
    """
    borrower_contract_id: str = "borrower_contract_id"
    original_principal: str = "original_principal"
    num_installments: str = "num_installments"
    interest_rate: str = "interest_rate"
    first_installment_date: str = "first_installment_date"
    periodicity: str = "periodicity"


DEFAULT_COLUMNS = LoanTapeColumns()

# ---------------------------------------------------------------------------
# Punto de entrada principal
# ---------------------------------------------------------------------------


def build_and_persist(
    loan_tape: pd.DataFrame,
    company_id: int,
    db_cfg: Optional[DBConfig] = None,
    columns: LoanTapeColumns = DEFAULT_COLUMNS,
) -> pd.DataFrame:
    """Construye el SPI desde el loan tape y lo persiste en MySQL.

    Args:
        loan_tape:  DataFrame con una fila por contrato. Debe tener las
                    columnas definidas en `columns`.
        company_id: ID numérico de la compañía.
        db_cfg:     Config de BD. Si None, lee de variables de entorno.
        columns:      Mapeo de nombres de columnas del loan tape.

    Returns:
        DataFrame con todos los installments generados, en formato sanitizado
        (columna installment_date).

    Raises:
        ValueError: Si el loan tape no tiene las columnas requeridas.
        RuntimeError: Si no se generó ningún installment o falló el INSERT.
    """
    required_cols = [
        columns.borrower_contract_id,
        columns.original_principal,
        columns.num_installments,
        columns.interest_rate,
        columns.first_installment_date,
    ]
    missing = [c for c in required_cols if c not in loan_tape.columns]
    if missing:
        raise ValueError(
            f"El loan tape no tiene las columnas requeridas para generar SPI: {missing}. "
            f"Columnas disponibles: {list(loan_tape.columns)}"
        )

    has_periodicity = columns.periodicity in loan_tape.columns

    all_installments: list[Installment] = []
    errors: list[str] = []

    for _, row in loan_tape.iterrows():
        contract_id = row[columns.borrower_contract_id]
        try:
            principal = Decimal(str(row[columns.original_principal]))
            num_inst = int(row[columns.num_installments])
            annual_rate = Decimal(str(row[columns.interest_rate]))

            raw_date = row[columns.first_installment_date]
            if isinstance(raw_date, str):
                first_date = date.fromisoformat(raw_date)
            elif hasattr(raw_date, "date"):
                # pandas Timestamp
                first_date = raw_date.date()
            else:
                first_date = raw_date  # already a date

            periodicity_raw = row[columns.periodicity] if has_periodicity else None
            periodicity = _normalize_periodicity(periodicity_raw)

            installments = build_schedule(
                borrower_contract_id=contract_id,
                principal=principal,
                annual_rate=annual_rate,
                num_installments=num_inst,
                first_installment_date=first_date,
                periodicity=periodicity,
            )
            all_installments.extend(installments)
            log.debug(
                "SPI generado: contract=%s | cuotas=%d | periodicidad=%s",
                contract_id, len(installments), periodicity,
            )

        except Exception as exc:
            log.error("Error generando SPI para contrato %s: %s", contract_id, exc)
            errors.append(f"{contract_id}: {exc}")

    if errors:
        log.warning(
            "%d contratos con error al generar SPI: %s",
            len(errors), errors,
        )

    if not all_installments:
        raise RuntimeError(
            f"No se pudo generar ningún installment para company_id={company_id}. "
            f"Errores: {errors}"
        )

    cfg = db_cfg or DBConfig.load()
    conn = connect(cfg)
    try:
        total = _insert_batch(conn, company_id, all_installments)
        conn.commit()
        log.info(
            "SPI persistido: %d cuotas para company_id=%s (%d contratos, %d con error)",
            total, company_id, len(loan_tape), len(errors),
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Devolver como DataFrame con installment_date para continuar el run sin releer la BD
    return pd.DataFrame([
        {
            "id": None,  # asignado por MySQL (auto-increment)
            "company_id": company_id,
            "borrower_contract_id": inst.borrower_contract_id,
            "borrower_installment_reference": str(inst.installment_number),
            "installment_date": inst.installment_date,
            "gross_amount": float(inst.gross_amount),
            "guarantee_amount": 0.0,
            "principal_amount": float(inst.principal_amount),
            "interest_amount": float(inst.interest_amount),
            "tax_amount": 0.0,
            "fee_amount": 0.0,
        }
        for inst in all_installments
    ])
