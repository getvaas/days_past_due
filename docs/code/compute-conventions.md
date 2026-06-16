# Convenciones del núcleo de cómputo (`modes/` y `products/`)

Patrones para la lógica pura de cálculo. Estas capas **no** acceden a BD ni AWS directamente.

## Modos (`dpd/modes/`)

Cada modo expone **dos funciones** con la misma semántica de salida:

```python
def compute_from_data(installments: Iterable[dict], payments: Iterable[dict],
                      cfg: RunConfig) -> Iterator[dict]:
    """Lógica pura sin BD. Esta es la función que se testea."""
    ...

def compute(conn, cfg: RunConfig) -> Iterator[dict]:
    """Trae los datos vía SQL y delega en compute_from_data()."""
    from ..integrations.db import cursor   # import local para no acoplar el módulo a MySQL
    ...
```

Reglas:
- **`compute_from_data` contiene TODA la lógica.** `compute` solo lee la BD y delega. No dupliques cálculo.
- Ambas funciones **devuelven un iterador de dicts** con exactamente: `{"id", "dpd_current", "amount_in_arrears"}`.
- El `import` de `integrations.db` es **local dentro de `compute()`**, no a nivel de módulo: mantiene el modo
  importable sin PyMySQL instalado.
- Re-ordená los datos por seguridad dentro de `compute_from_data` (el SQL ya viene ordenado, pero los datos
  sintéticos de tests no necesariamente).
- Lee parámetros opcionales de forma defensiva: `getattr(cfg, "paid_threshold", 1.0)`.

## Productos (`dpd/products/`)

Cada producto expone una única función `compute(...)` que **recibe y devuelve el loan tape**:

```python
def compute(loan_tape: pd.DataFrame, ..., key: str, ...) -> pd.DataFrame:
    """Calcula la columna del producto y la agrega al loan tape (merge por `key`)."""
    out = loan_tape.copy()
    out = out.merge(per_contract.rename(columns={"borrower_contract_id": key}), on=key, how="left")
    out["<columna>"] = out["<columna>"].fillna(...)
    return out
```

Reglas:
- **Nunca mutar el `loan_tape` de entrada** — siempre `loan_tape.copy()` antes de modificar.
- `key` es el nombre de la columna de contrato en el loan tape; se hace merge contra `borrower_contract_id` del SPI/payments
  renombrando ese lado a `key`.
- **Manejar el caso vacío** explícitamente: si no hay datos, agregar la columna con su valor neutro (0 / 0.0) y retornar.
- `fillna()` tras el `LEFT JOIN` para contratos sin match.
- Reutilizá los sanitizadores y conversores de `excel_runner` (`sanitize_schedule`, `sanitize_payment_tape`,
  `_installments_from_df`, `_payments_from_df`) en vez de reimplementarlos.

## Sanitización: misma entrada sin importar el origen

`excel_runner.sanitize_schedule()` y `sanitize_payment_tape()` normalizan los datos vengan de Excel o de MySQL:
fechas a `datetime.date`, `borrower_installment_reference` a `str`, buckets vacíos a 0, id sintético si falta.
Los productos detectan si el input ya está sanitizado mirando si existe la columna `installment_date`/`payment_date`.

## Do / Don't

| ✅ Do | ❌ Don't |
|-------|---------|
| Toda la lógica en `compute_from_data` | Lógica distinta entre `compute` y `compute_from_data` |
| `loan_tape.copy()` antes de agregar columnas | Mutar el DataFrame de entrada |
| Manejar `df.empty` con valor neutro | Asumir que siempre hay filas |
| `import` de `integrations.db` local en `compute()` | Importar PyMySQL a nivel de módulo en `modes/` |
| Reusar sanitizadores de `excel_runner` | Reparsear fechas/refs a mano en cada producto |
