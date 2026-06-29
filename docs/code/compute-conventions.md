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
- Reutilizá los conversores polars→dicts de `products/dpd.py` (`_installments_from_pl`, `_payments_from_pl`)
  en vez de reimplementarlos. Los datos llegan ya sanitizados desde los loaders de `db_reader`.

## Sanitización: en los loaders de `db_reader`

`db_reader._sanitize_schedule()` y `_sanitize_payment_tape()` normalizan los datos leídos de MySQL:
fechas a `date`, `borrower_installment_reference` a `str`, buckets vacíos a 0, id sintético si falta.
Los loaders devuelven **polars DataFrames** listos para los productos.

## Do / Don't

| ✅ Do | ❌ Don't |
|-------|---------|
| Toda la lógica en `compute_from_data` | Lógica distinta entre `compute` y `compute_from_data` |
| `loan_tape.copy()` antes de agregar columnas | Mutar el DataFrame de entrada |
| Manejar `df.empty` con valor neutro | Asumir que siempre hay filas |
| La lectura de BD vive en `db_reader` (loaders) | Que los `modes/` lean MySQL |
| Reusar conversores `_*_from_pl` y los loaders de `db_reader` | Reparsear fechas/refs a mano en cada producto |
