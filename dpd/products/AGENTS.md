# AGENTS.md — dpd/products/

**Columnas derivadas** que se agregan al loan tape (una fila por contrato). Lógica pura sobre DataFrames.

- `dpd.py` — `dpd_current`, `dpd_max` (high-watermark histórico), `amount_in_arrears`.
- `total_amount.py` — `total_amount_paid`.
- `vpn.py` — `vpn` (valor presente neto de cuotas futuras descontadas).

## Antes de editar, leé

- Qué calcula cada producto: [../../docs/business/products.md](../../docs/business/products.md)
- Patrón `compute(loan_tape, ..., key) -> loan_tape`: [../../docs/code/compute-conventions.md](../../docs/code/compute-conventions.md)

## Reglas locales

- Firma uniforme: `compute(loan_tape: pd.DataFrame, ..., key: str, ...) -> pd.DataFrame`.
- **Nunca mutar el `loan_tape` de entrada** → `loan_tape.copy()` y merge por `key` (renombrando `borrower_contract_id`→`key`).
- **Manejar el caso vacío**: agregar la columna con valor neutro (0 / 0.0) y retornar.
- `dpd.py` usa el modo de cálculo de `../modes/` y, para `dpd_max`, lee `previous_output` (output previo de S3);
  `dpd_max = max(dpd_current, dpd_max_previo)` y **nunca decrece**.
- `vpn.py` usa la tasa **del mensaje** (`metadata.interest_rate`), no la del loan tape.
- Los datos llegan ya sanitizados desde los loaders polars de `db_reader` (`load_schedule` / `load_payment_tape`).
  Para pasar de polars a `list[dict]` para los modos, reusar `_installments_from_pl` / `_payments_from_pl` de `dpd.py`.
