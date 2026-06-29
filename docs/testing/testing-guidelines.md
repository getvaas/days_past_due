# Guías de testing (a implementar)

> ⚠ **Estado actual:** el proyecto **no tiene tests unitarios** todavía. Solo existe un smoke test de integración
> contra MySQL (`tests/run.sh`) que además está **roto** (invoca `python -m dpd.main`, un entry point eliminado
> en el refactor a `integrations/`). Este documento define la **estrategia objetivo a implementar**, no lo que hoy existe.

## Objetivo de cobertura

| Prioridad | Capa | Objetivo | Por qué |
|-----------|------|----------|---------|
| **Alta** | `modes/` (`compute_from_data`) | ~80% | Lógica pura de mora: join vs cascade, buckets, thresholds. Sin BD ni AWS. |
| **Alta** | `products/` (`compute`) | ~80% | dpd_current/dpd_max, total_amount, vpn. Merge por `key`, casos vacíos. |
| **Alta** | `spi_builder` (`build_schedule`, `_period_rate`, `_add_months`) | ~80% | Amortización PMT, conversión de tasa, fechas por periodicidad. Sin el `INSERT`. |
| Media | `db_reader` (loaders + sanitizadores polars) | razonable | Normalización de datos crudos de MySQL. |
| Baja | `utils/s3`, `sns_publisher`, `lambda_handler`, `batch_handler`, `processor` | opcional | IO/orquestación: mockear boto3/PyMySQL si se cubren. |

El foco acordado es el **núcleo de cálculo** (`modes/` + `products/`): es lógica pura, determinista y de alto
valor de negocio, testeable sin infraestructura.

## Qué testear (núcleo)

- **`modes/cascade_fifo.compute_from_data`**: orden de drenado FIFO, excedente que fluye a la cuota siguiente,
  orden de buckets (`guarantee → principal → interest → moratory → tax → fee`), `partial_payment_counts`,
  `paid_threshold`, `grace_days`. Casos del seed (`C001`–`C005`) son fixtures naturales.
- **`modes/join_installment.compute_from_data`**: agregación por `(contract, installment_reference)`, pagos sin
  referencia ignorados, comparación contra `gross × threshold`. Contraste con cascade (caso `C002`).
- **`products/dpd.compute`**: `dpd_current` = max por contrato; `amount_in_arrears` solo en cuotas con `dpd > 0`;
  `dpd_max` como high-watermark (con y sin `previous_output`); caso sin resultados.
- **`products/vpn.compute`**: descuento de cuotas futuras, `r=0`/`None` → sin descuento, sin cuotas futuras → 0.
- **`products/total_amount.compute`**: suma por contrato, payments vacío, pagos `<= 0` descartados.
- **`spi_builder`**: PMT con tasa > 0 y tasa 0, última cuota que liquida el saldo, `_period_rate` por periodicidad,
  `_add_months` con meses cortos (ej. 31 ene → feb), `_normalize_periodicity` con alias en español.

## Qué NO testear (o aislar con mocks)

- El `INSERT`/`commit` de `spi_builder` y los `SELECT` reales: cubrir con integración (Docker) o mockear la conexión.
- boto3 (S3/SNS): mockear el cliente; no pegarle a AWS real en unit tests.
- El parseo de Excel real puede usar el fixture `tests/Days Past Due.xlsx`.

## Estrategia general

- **Runner: abierto** — no se fija un framework. Recomendación: tests unitarios sin dependencias de red/Docker;
  integración separada contra MySQL descartable (ver [run-tests.md](run-tests.md)).
- Determinismo: pasar siempre `calc_date` explícito en los tests (nunca depender de `date.today()`).
- Comparaciones monetarias con `Decimal`, no `float`.

Convenciones de archivos y estructura de tests: [test-conventions.md](test-conventions.md).
