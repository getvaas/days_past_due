# Days Past Due (DPD) — Payments Expand

Cálculo de **morosidad (Days Past Due)** y productos derivados sobre el loan tape de una compañía.
El núcleo de procesamiento ([dpd/processor.py](dpd/processor.py)) es compartido por dos puntos de entrada
productivos y un runner local:

1. **AWS Lambda** ([dpd/lambda_handler.py](dpd/lambda_handler.py)) — escucha SQS, decide procesar inline o derivar a AWS Batch (según el tamaño del loan tape), calcula y publica en SNS.
2. **AWS Batch** ([dpd/batch_handler.py](dpd/batch_handler.py)) — para loan tapes grandes; ejecuta el mismo `processor` inline (nunca re-encola).
3. **Runner local** ([dpd/local_runner.py](dpd/local_runner.py)) — ejecuta el flujo desde un evento JSON, sin AWS real.

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

### 1. Como Lambda (Payments Expand)

[dpd/lambda_handler.py](dpd/lambda_handler.py) — entry point `handler(event, context)`. Flujo por mensaje SQS:

1. Parsear mensaje SQS → `InboundMessage`
2. Leer loan tape (input) desde S3
3. **Si el loan tape supera `BATCH_ROW_THRESHOLD`** → encolar un job de AWS Batch y retornar; si no, procesar inline (vía `processor.process_loan_tape`)
4. Leer SPI + payment tape desde MySQL (`db_reader`)
5. Calcular los productos pedidos en `metadata.products`
6. Agregar columnas de trazabilidad (`last_update_date`, `payment_tape_ref`)
7. Escribir loan tape enriquecido en S3 (`output_file`)
8. Publicar respuesta en SNS con `MessageAttributes` (`origin`/`target`) para el filtro de suscripción

> La decisión de derivar a Batch vive **solo** en `lambda_handler`. El job de Batch usa `processor` directamente
> (no conoce el umbral), así que procesa inline y nunca vuelve a encolar otro job.

### 2. Como job de AWS Batch

```bash
python -m dpd.batch_handler --payload '{"origin": "ENRICHER", "target": "PAYMENTS_EXPAND", ...}'
```

El payload también puede llegar por la variable de entorno `DPD_BATCH_PAYLOAD`. Ejecuta el mismo procesamiento que el camino inline de la Lambda.

### 3. Runner local (sin AWS real)

```bash
python -m dpd.local_runner --event evento.json            # ejecuta el handler
python -m dpd.local_runner --event evento.json --dry-run  # solo parsea/valida
```

Variables de entorno: `SNS_RESPONSE_TOPIC_ARN`, credenciales de BD (vía Secrets Manager en la nube), y
`BATCH_JOB_QUEUE` / `BATCH_JOB_DEFINITION` / `BATCH_ROW_THRESHOLD`.
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
4. Devuelve el DataFrame en el mismo formato que los loaders de `db_reader` para continuar el run sin releer la BD

Si el loan tape usa nombres de columna distintos, se puede configurar vía `LoanTapeColumns`:
```python
from dpd.spi_builder import build_and_persist, LoanTapeColumns
spi_df = build_and_persist(
    loan_tape=df,
    company_id=86,
    columns=LoanTapeColumns(original_principal="disbursement_amount"),
)
```

Para `rate_type='variable'` el SPI debe cargarse manualmente — la Lambda lanza `NotImplementedError` en ese caso.

---

## Estructura

```
dpd/
├── lambda_handler.py        # entry point Lambda: decide inline vs Batch
├── batch_handler.py         # entry point AWS Batch (procesa inline vía processor)
├── local_runner.py          # runner local desde evento JSON
├── processor.py             # núcleo: lee datos → productos → S3 → SNS (compartido)
├── batch_submitter.py       # encola jobs en AWS Batch (usado solo por lambda_handler)
├── models.py                # protocolo de mensajes SQS/SNS
├── config/                  # DBConfig (env/Secrets Manager) + RunConfig + constantes Batch
├── db_reader.py             # lectura de MySQL: load_schedule/load_payment_tape (polars) + read_last_dates
├── spi_builder.py           # genera SPI desde loan tape (PMT) y persiste en MySQL
├── sns_publisher.py         # publicación de respuesta en SNS
├── modes/
│   ├── join_installment.py  # Modo 1: join por referencia de cuota
│   └── cascade_fifo.py      # Modo 2: cascada FIFO
├── products/
│   ├── dpd.py               # dpd_current / amount_in_arrears
│   ├── total_amount.py      # total_amount_paid
│   └── vpn.py               # valor presente neto
├── utils/
│   ├── aws_boto_session.py  # sesión boto3
│   ├── s3.py                # read/write loan tape en S3 (csv/parquet)
│   ├── decimals.py          # to_decimal()
│   └── dates.py             # to_date()
└── integrations/
    └── db.py                # wrapper PyMySQL (connect/cursor/connection, SQL crudo, sin ORM)
```

---

## Tests

Runner canónico basado en Docker (definido en `.sdd.json`):

```bash
./scripts/run-tests.sh
```

Los tests unitarios mockean BD/AWS (no requieren servicios). Los tests marcados `@pytest.mark.integration`
([tests/test_dpd_integration.py](tests/test_dpd_integration.py)) requieren un MySQL local y se **skipean**
automáticamente si la BD no está disponible.
