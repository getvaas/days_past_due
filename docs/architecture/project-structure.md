# Estructura del proyecto

Árbol de carpetas del paquete `dpd/` con la responsabilidad de cada archivo. Un agente debería poder elegir
el archivo correcto por su nombre y esta descripción, sin abrirlos todos.

## Árbol

```
dpd/
├── __init__.py
├── lambda_handler.py        # Entry point AWS Lambda: SQS → cálculo → SNS. Orquesta todo el flujo.
├── models.py                # Protocolo de mensajes SQS/SNS (InboundMessage, OutboundMessage, MessageMetadata).
├── config.py                # DBConfig (credenciales desde .env) + RunConfig (parámetros de cálculo).
├── excel_runner.py          # Carga/sanitiza Excel + compute_dpd(): NÚCLEO de cómputo compartido. CLI propio.
├── db_reader.py             # SELECTs a MySQL para la Lambda (read_schedule, read_payments, read_last_dates).
├── spi_builder.py           # Genera SPI (amortización PMT) desde el loan tape y lo persiste en MySQL.
├── s3_io.py                 # read/write del loan tape en S3 (csv/parquet) vía boto3.
├── sns_publisher.py         # publish_response(): publica el OutboundMessage en SNS con MessageAttributes.
├── modes/                   # CÓMPUTO PURO — cómo se asignan los pagos a las cuotas.
│   ├── join_installment.py  #   Modo 1: join cuota↔pagos por borrower_installment_reference.
│   └── cascade_fifo.py      #   Modo 2: cascada FIFO, el excedente fluye a la cuota siguiente.
├── products/                # CÓMPUTO PURO — columnas derivadas que se agregan al loan tape.
│   ├── dpd.py               #   dpd_current, dpd_max (high-watermark), amount_in_arrears.
│   ├── total_amount.py      #   total_amount_paid.
│   └── vpn.py               #   vpn (valor presente neto de cuotas futuras).
└── integrations/            # Acceso a MySQL y runner MySQL→Excel (solo lectura).
    ├── db.py                #   Wrapper fino PyMySQL (connect, cursor). SQL crudo, sin ORM.
    ├── queries.py           #   Summary queries por contrato (current_dpd / max_dpd).
    └── db_excel_runner.py   #   Entry point: lee MySQL (solo lectura) y exporta DPD a Excel.
```

## Raíz del repo

| Archivo/carpeta | Rol |
|-----------------|-----|
| `README.md` | Documentación funcional de referencia (conceptos, uso de cada entry point). |
| `requirements.txt` | Dependencias: PyMySQL, pandas, boto3, pyarrow, openpyxl, python-dateutil. |
| `.env` / `.env.example` | Credenciales de BD. Auto-cargado por `config.py` al importar. |
| `tests/` | Fixtures de integración (schema.sql, seed.sql, verify.sql) + `run.sh` (smoke, ⚠ roto). |
| `revisar_archivos.ipynb` | Notebook de análisis ad-hoc. No es referencia de convenciones. |

## Cómo navegar según la tarea

| Quiero… | Voy a… |
|---------|--------|
| Cambiar cómo se asignan pagos a cuotas | `modes/` + [business/calculation-modes.md](../business/calculation-modes.md) |
| Agregar/editar una columna derivada | `products/` + [business/products.md](../business/products.md) |
| Tocar el flujo Lambda (SQS/SNS/S3) | `lambda_handler.py`, `s3_io.py`, `sns_publisher.py`, `models.py` |
| Cambiar lectura de MySQL | `db_reader.py`, `integrations/` |
| Generación automática de calendario | `spi_builder.py` + [business/products.md](../business/products.md) |
