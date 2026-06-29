# Convenciones de tests (a implementar)

> ⚠ Aún no existen tests unitarios. Estas son las convenciones recomendadas para cuando se implementen. El runner
> quedó **abierto**; los ejemplos usan `pytest` por ser el estándar de facto en Python, pero no es obligatorio.

## Ubicación y nombres

- Tests en `tests/`, junto a los fixtures actuales (`schema.sql`, `seed.sql`, `Days Past Due.xlsx`).
- Un archivo por módulo bajo prueba: `test_<modulo>.py` (ej. `test_cascade_fifo.py`, `test_dpd_product.py`,
  `test_spi_builder.py`).
- Nombres de tests descriptivos del comportamiento: `test_cascade_overflow_fluye_a_siguiente_cuota`,
  `test_dpd_max_no_decrece_con_output_previo`.

## Estructura de un test (Arrange-Act-Assert)

```python
from datetime import date
from decimal import Decimal
from dpd.config import RunConfig
from dpd.modes import cascade_fifo

def test_cascade_pago_unico_cubre_dos_cuotas():
    # Arrange — datos sintéticos como listas de dicts (mismo shape que compute_from_data espera)
    installments = [
        {"id": 1, "borrower_contract_id": "C005", "installment_date": date(2026, 3, 1),
         "gross_amount": 1000, "guarantee_amount": 0, "principal_amount": 800,
         "interest_amount": 150, "tax_amount": 30, "fee_amount": 20},
        {"id": 2, "borrower_contract_id": "C005", "installment_date": date(2026, 4, 1),
         "gross_amount": 1000, "guarantee_amount": 0, "principal_amount": 800,
         "interest_amount": 150, "tax_amount": 30, "fee_amount": 20},
    ]
    payments = [{"borrower_contract_id": "C005", "payment_date": date(2026, 3, 1),
                 "total_payment": 1500}]
    cfg = RunConfig(company_id=0, company_code="*", mode="cascade",
                    partial_payment_counts=False, calculation_date=date(2026, 5, 4), grace_days=1)

    # Act
    results = {r["id"]: r for r in cascade_fifo.compute_from_data(installments, payments, cfg)}

    # Assert
    assert results[1]["dpd_current"] == 0           # cuota 1 cubierta
    assert results[2]["dpd_current"] > 0             # cuota 2 sin pool suficiente
    assert results[2]["amount_in_arrears"] == Decimal("500")
```

## Reglas

- **Testear `compute_from_data` / `compute` puro**, no `compute(conn, cfg)` con BD real.
- **`calc_date` siempre explícito.** Nunca depender de `date.today()` (los tests deben ser deterministas).
- **Aritmética monetaria con `Decimal`**, igual que el código de producción.
- Para productos (`products/`): construir `loan_tape` como `pd.DataFrame` y verificar las columnas agregadas y que
  no se mutó el DataFrame de entrada.
- Reutilizar los fixtures del seed: los escenarios `C001`–`C005` ya tienen resultados esperados documentados en
  [tests/seed.sql](../../tests/seed.sql).
- Mocks de IO: parchear `boto3.client` para `utils/s3`/`sns_publisher`; parchear `db_reader.connection` (o
  `integrations.db.connect`) para cubrir `db_reader`/`spi_builder` sin MySQL.

## Fixtures compartidos

- `tests/Days Past Due.xlsx` — dataset de ejemplo (legacy; ya no lo consume código del paquete).
- `tests/seed.sql` — escenarios con resultados esperados (días de mora calculados para `calc_date=2026-05-04`).

Cómo ejecutar: [run-tests.md](run-tests.md).
