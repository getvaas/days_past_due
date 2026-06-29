# Estructura del proyecto

Árbol de carpetas del paquete `dpd/` con la responsabilidad de cada archivo. Un agente debería poder elegir
el archivo correcto por su nombre y esta descripción, sin abrirlos todos.

## Árbol

```
dpd/
├── __init__.py
├── lambda_handler.py        # Entry point AWS Lambda: SQS → decide inline vs Batch → delega en processor. Aquí vive la decisión de derivar a Batch.
├── batch_handler.py         # Entry point AWS Batch (python -m dpd.batch_handler): procesa inline vía processor, nunca re-encola.
├── local_runner.py          # Runner local: ejecuta el handler desde un evento JSON (sin AWS real).
├── processor.py             # NÚCLEO de orquestación: lee datos, calcula productos, escribe S3 y publica SNS. Compartido por Lambda y Batch.
├── models.py                # Protocolo de mensajes SQS/SNS (InboundMessage, OutboundMessage, MessageMetadata).
├── config/                  # DBConfig (credenciales desde .env/Secrets Manager) + RunConfig (parámetros de cálculo) + constantes Batch.
├── db_reader.py             # Lectura de payments_db: load_schedule/load_payment_tape (→ polars) + read_last_dates.
├── spi_builder.py           # Genera SPI (amortización PMT) desde el loan tape y lo persiste en MySQL.
├── batch_submitter.py       # submit_job(): encola un job en AWS Batch (usado solo por lambda_handler).
├── sns_publisher.py         # publish_response(): publica el OutboundMessage en SNS con MessageAttributes.
├── modes/                   # CÓMPUTO PURO — cómo se asignan los pagos a las cuotas.
│   ├── join_installment.py  #   Modo 1: join cuota↔pagos por borrower_installment_reference.
│   └── cascade_fifo.py      #   Modo 2: cascada FIFO, el excedente fluye a la cuota siguiente.
├── products/                # CÓMPUTO PURO — columnas derivadas que se agregan al loan tape (polars).
│   ├── dpd.py               #   dpd_current, amount_in_arrears (carga datos y delega en modes/).
│   ├── total_amount.py      #   total_amount_paid.
│   └── vpn.py               #   vpn (valor presente neto de cuotas futuras).
├── utils/                   # Helpers transversales.
│   ├── aws_boto_session.py  #   Sesión boto3 (perfil local vs rol Lambda).
│   ├── s3.py                #   read/write del loan tape en S3 (csv/parquet) vía boto3.
│   ├── decimals.py          #   to_decimal(): conversión robusta a Decimal (None/NaN → 0).
│   └── dates.py             #   to_date(): parseo robusto a date (str ISO / datetime / date).
└── integrations/            # Acceso a MySQL.
    └── db.py                #   Wrapper fino PyMySQL (connect, cursor, connection). SQL crudo, sin ORM.
```

## Raíz del repo

| Archivo/carpeta | Rol |
|-----------------|-----|
| `README.md` | Documentación funcional de referencia (conceptos, uso de cada entry point). |
| `requirements.txt` | Dependencias: PyMySQL, polars, pandas (solo spi_builder), boto3, pyarrow, python-dateutil. |
| `.env` / `.env.example` | Credenciales de BD. Auto-cargado por `config/` al importar. |
| `tests/` | Fixtures de integración (schema.sql, seed.sql, verify.sql) + `run.sh` (smoke, ⚠ roto). |
| `revisar_archivos.ipynb` | Notebook de análisis ad-hoc. No es referencia de convenciones. |

## Cómo navegar según la tarea

| Quiero… | Voy a… |
|---------|--------|
| Cambiar cómo se asignan pagos a cuotas | `modes/` + [business/calculation-modes.md](../business/calculation-modes.md) |
| Agregar/editar una columna derivada | `products/` + [business/products.md](../business/products.md) |
| Tocar el flujo de cálculo (lee datos → productos → S3 → SNS) | `processor.py`, `utils/s3.py`, `sns_publisher.py`, `models.py` |
| Tocar la decisión Lambda vs Batch | `lambda_handler.py`, `batch_handler.py`, `batch_submitter.py` |
| Cambiar lectura de MySQL | `db_reader.py`, `integrations/` |
| Generación automática de calendario | `spi_builder.py` + [business/products.md](../business/products.md) |
