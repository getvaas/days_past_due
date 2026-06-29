"""Conversión robusta a Decimal para cálculo monetario.

Compartido por los modos de cálculo. Maneja None y NaN (celdas vacías que
pandas/polars representan como float('nan')) devolviendo Decimal(0), y usa
str() para evitar imprecisión al convertir floats.
"""
from __future__ import annotations

from decimal import Decimal


def to_decimal(v) -> Decimal:
    """Devuelve Decimal(v). None y NaN → Decimal(0)."""
    if v is None:
        return Decimal(0)
    # pandas/polars representan celdas vacías como float('nan'); tratarlas como 0.
    if isinstance(v, float) and v != v:  # NaN
        return Decimal(0)
    # str() para evitar imprecisión cuando el dato viene como float.
    return Decimal(str(v))
