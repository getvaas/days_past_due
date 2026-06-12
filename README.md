# Days Past Due (DPD) — Payments Expand

Cálculo de **morosidad (Days Past Due)** y productos derivados sobre el loan tape de una compañía.
El núcleo de cómputo es puro (sin BD ni AWS) y se reutiliza desde tres puntos de entrada:

1. **AWS Lambda** ([dpd/lambda_handler.py](dpd/lambda_handler.py)) — escucha SQS, calcula, publica en SNS.
2. **Excel** ([dpd/excel_runner.py](dpd/excel_runner.py)) — corre DPD sobre archivos planos, sin MySQL.
3. **MySQL → Excel** ([dpd/integrations/db_excel_runner.py](dpd/integrations/db_excel_runner.py)) — lee de BD (solo lectura) y exporta a Excel.

---

## Conceptos

- **Cuota** (`scheduled_payments_installments`, *SPI*): una fila por vencimiento programado, con `gross_amount` y su desglose en buckets (`principal`, `interest`, `guarantee`, `tax`, `fee`).
- **Pago** (`payment_tape`): una fila por pago recibido, con `total_payment`.
- **DPD**: días calendario desde el vencimiento de una cuota impaga, menos los días de gracia (`grace_days`, default **1**).
- **`paid_threshold`**: fracción mínima pagada para considerar una cuota "al día" (default `1.0` = 100%).
- **`dpd_max`**: high-watermark histórico. Se calcula como `max(dpd_max_previo, dpd_current)` leyendo el output del run anterior desde S3. Nunca decrece.
- **`rate_type`**: `"fixed"` | `"variable"`. Para tasa variable el SPI debe cargarse manualmente — la generación automática no aplica porque la cuota cambia período a período.
- **Filtro por compañía**: cada tabla se filtra por su propia columna y **no coinciden**:
  - `payment_tape.company_id` → numérico (ej. `86`)
  - `scheduled_payments_installments.company_code` → string (ej. `"sistecredito"`)

### Tasas de interés — dos fuentes distintas

| Uso | Fuente | Descripción |
|-----|--------|-------------|
| **Generación de SPI** | Columna `interest_rate` del loan tape | Tasa por contrato (deudor). Puede variar entre créditos del mismo portafolio. |
| **Cálculo de VPN** | `metadata.interest_rate` en el mensaje SQS | Tasa del tranche (tasa de descuento del fondo/inversionista). Es una sola tasa por mensaje. |

Mezclarlas produce resultados incorrectos. El `spi_builder` usa la del loan tape; `products/vpn.py` usa la del mensaje.

### Modos de cálculo

| Modo | Módulo | Cómo asigna los pagos |
|------|--------|-----------------------|
| **`join`** | [dpd/modes/join_installment.py](dpd/modes/join_installment.py) | Une cuota ↔ pagos por `borrower_installment_reference` y compara `SUM(total_payment)` contra `gross_amount`. |
| **`cascade`** | [dpd/modes/cascade_fifo.py](dpd/modes/cascade_fifo.py) | FIFO: acumula todos los pagos del contrato en un pool y los drena cuota por cuota en orden de fecha. El excedente fluye a la siguiente cuota. |

Orden de aplicación de buckets en cascade: `guarantee → principal → interest → moratory_interest → tax → fee`.

### Productos

| Producto | Módulo | Columna(s) que agrega |
|----------|--------|------------------------|
| `dpd` | [dpd/products/dpd.py](dpd/products/dpd.py) | `dpd_current`, `dpd_max` (high-watermark histórico), `amount_in_arrears` |
| `total_amount` | [dpd/products/total_amount.py](dpd/products/total_amount.py) | `total_amount_paid` |
| `vpn` | [dpd/products/vpn.py](dpd/products/vpn.py) | `vpn` (valor presente neto de cuotas futuras descontadas a `interest_rate`) |

---

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Las credenciales de BD se cargan automáticamente desde un `.env` en la raíz del repo (ver [.env.example](.env.example)):

```bash
cp .env.example .env   # y completá los valores
```

```
DB_HOST=
DB_PORT=3306
DB_NAME=
DB_USER=
DB_PASSWORD=
```

---

## Uso

### 1. Desde Excel (sin BD)

```bash
python -m dpd.excel_runner \
    --schedule "tests/Days Past Due.xlsx" \
    --payment-tape "tests/Days Past Due.xlsx" \
    --date 2026-10-03 \
    --mode cascade \
    --out resultado_dpd.xlsx
```

Flags: `--mode {cascade,join,both}`, `--grace-days N`, `--partial-counts`, `--schedule-sheet`, `--pt-sheet`.
Genera un Excel con dos hojas: `schedule_con_dpd` (detalle por cuota) y `resumen_por_contrato`.

### 2. Desde MySQL (solo lectura → Excel)

Análisis del día anterior de una compañía. Pregunta `company_id`/`company_code` si no se pasan:

```bash
python -m dpd.integrations.db_excel_runner \
    --company-id 86 --company-code sistecredito --date 2026-06-01
```

### 3. Como Lambda (Payments Expand)

[dpd/lambda_handler.py](dpd/lambda_handler.py) — entry point `handler(event, context)`. Flujo por mensaje SQS:

1. Parsear mensaje SQS → `InboundMessage`
2. Leer loan tape (input) + output previo desde S3 (para recuperar `dpd_max`)
3. Leer SPI + payment tape desde MySQL. Si el SPI está vacío y `rate_type='fixed'` → generarlo desde el loan tape y persistirlo (ver `spi_builder.py`)
4. Calcular los productos pedidos en `metadata.products`
5. Agregar columnas de trazabilidad (`last_update_date`, `payment_tape_ref`)
6. Escribir loan tape enriquecido en S3 (`output_file`)
7. Publicar respuesta en SNS con `MessageAttributes` (`origin`/`target`) para el filtro de suscripción

Variables de entorno: `SNS_RESPONSE_TOPIC_ARN` + las de BD (`DB_*`).
El protocolo de mensajes (`InboundMessage`/`OutboundMessage`/`MessageMetadata`) está en [dpd/models.py](dpd/models.py).

---

## Generación automática de SPI (`spi_builder.py`)

Cuando la Lambda consulta `scheduled_payments_installments` y la tabla está vacía para la compañía (primer run de un originador nuevo), y `rate_type='fixed'`, el módulo [dpd/spi_builder.py](dpd/spi_builder.py) genera el calendario automáticamente desde el loan tape y lo persiste en MySQL.

**Columnas requeridas en el loan tape:**

| Columna | Descripción |
|---------|-------------|
| `borrower_contract_id` | Identificador del crédito |
| `original_principal` | Monto original desembolsado |
| `num_installments` | Número de cuotas |
| `interest_rate` | Tasa anual efectiva (ej. `0.24` = 24%) |
| `first_installment_date` | Fecha de la primera cuota |
| `periodicity` | `monthly` / `biweekly` / `weekly` / `daily` — si vacío asume `monthly` |

**Lógica:**

1. Convierte la tasa anual efectiva a tasa periódica: `(1 + r_anual)^(1/n) - 1`
2. Genera amortización de cuota fija (PMT): `pmt = P × r / (1 − (1+r)^−n)`
3. Hace `INSERT` batch en `scheduled_payments_installments` y `COMMIT`
4. Devuelve el DataFrame en el mismo formato que `db_reader.read_schedule` para continuar el run sin releer la BD

Si el loan tape usa nombres de columna distintos, se puede configurar vía `LoanTapeColumns`:
```python
from dpd.spi_builder import build_and_persist, LoanTapeColumns
spi_df = build_and_persist(
    loan_tape=df,
    company_code="finkargo",
    columns=LoanTapeColumns(original_principal="disbursement_amount"),
)
```

Para `rate_type='variable'` el SPI debe cargarse manualmente — la Lambda lanza `NotImplementedError` en ese caso.

---

## Estructura

```
dpd/
├── lambda_handler.py        # entry point Lambda (SQS → SNS)
├── models.py                # protocolo de mensajes SQS/SNS
├── config.py                # DBConfig (env) + RunConfig (parámetros de cálculo)
├── excel_runner.py          # carga Excel, sanitiza, compute_dpd() — núcleo de cómputo
├── db_reader.py             # SELECTs a MySQL para la Lambda
├── spi_builder.py           # genera SPI desde loan tape (PMT) y persiste en MySQL
├── s3_io.py                 # read/write loan tape en S3 (csv/parquet)
├── sns_publisher.py         # publicación de respuesta en SNS
├── modes/
│   ├── join_installment.py  # Modo 1: join por referencia de cuota
│   └── cascade_fifo.py      # Modo 2: cascada FIFO
├── products/
│   ├── dpd.py               # dpd_current / dpd_max / amount_in_arrears
│   ├── total_amount.py      # total_amount_paid
│   └── vpn.py               # valor presente neto
└── integrations/
    ├── db.py                # wrapper PyMySQL (SQL crudo, sin ORM)
    ├── queries.py           # summary queries por contrato (solo lectura)
    └── db_excel_runner.py   # MySQL (solo lectura) → Excel
```

---

## Tests

Smoke test de integración contra un MySQL descartable (requiere Docker):

```bash
./tests/run.sh join                      # Modo 1
./tests/run.sh cascade                   # Modo 2
./tests/run.sh cascade --partial-counts
```

Levanta un contenedor `dpd-mysql`, aplica `tests/schema.sql` + `tests/seed.sql`, corre el job e imprime `tests/verify.sql`. Borralo con `docker rm -f dpd-mysql`.

> ⚠ **Pendiente:** [tests/run.sh](tests/run.sh) todavía invoca `python -m dpd.main`, un entry point que se eliminó en el refactor a `integrations/`. Mientras no se actualice, para correr DPD contra MySQL usá [dpd/integrations/db_excel_runner.py](dpd/integrations/db_excel_runner.py) (ver sección Uso §2).
