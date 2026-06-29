# AGENTS.md — dpd/modes/

Modos de **asignación de pagos a cuotas** (lógica pura, sin BD ni AWS). Cada modo decide qué cuotas están pagas
y calcula `{id, dpd_current, amount_in_arrears}`.

- `join_installment.py` — Modo 1: une cuota↔pagos por `borrower_installment_reference`.
- `cascade_fifo.py` — Modo 2: cascada FIFO, el excedente del pago fluye a la cuota siguiente.

## Antes de editar, leé

- Comportamiento de cada modo: [../../docs/business/calculation-modes.md](../../docs/business/calculation-modes.md)
- Patrón `compute` / `compute_from_data` y reglas de capa: [../../docs/code/compute-conventions.md](../../docs/code/compute-conventions.md)

## Reglas locales

- **Toda la lógica vive en `compute_from_data(installments, payments, cfg)`** (función pura testeable).
  La lectura de BD vive en `db_reader` (loaders); los modos NO leen la BD.
- Aritmética con `Decimal`: usar `to_decimal` de [../utils/decimals.py](../utils/decimals.py) (trata NaN y None como 0).
- Orden de buckets en cascade: `guarantee → principal → interest → moratory_interest → tax → fee`.
- Salida: iterador de dicts `{"id", "dpd_current", "amount_in_arrears"}`.
