"""Parseo robusto a datetime.date.

Compartido por el parseo de mensajes (models) y la lectura de fechas de BD
(db_reader). Acepta None, date, datetime (de PyMySQL) y strings ISO.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional


def to_date(v) -> Optional[date]:
    """Normaliza un valor a date. None → None; datetime → su fecha; str ISO → date."""
    if v is None:
        return None
    if isinstance(v, datetime):  # datetime es subclase de date → normalizar primero
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v))
