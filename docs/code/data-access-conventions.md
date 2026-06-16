# Convenciones de acceso a datos (MySQL, S3, SNS)

Patrones para las capas de IO: `integrations/`, `db_reader.py`, `spi_builder.py`, `s3_io.py`, `sns_publisher.py`.

## MySQL — `integrations/db.py`

Wrapper fino de PyMySQL. **SQL crudo a propósito, sin ORM.**

```python
conn = connect(cfg)          # cfg: DBConfig
try:
    with cursor(conn) as cur:     # DictCursor por default
        cur.execute(SOME_SQL, {"company_code": str(code)})
        rows = cur.fetchall()
finally:
    conn.close()
```

- `connect()` abre con `autocommit=False`. Las **lecturas** cierran la conexión en `finally`.
- Para **escrituras** (`spi_builder`): `conn.commit()` explícito en éxito, `conn.rollback()` en except, `close()` en finally.
- El SQL vive **junto a su consumidor**, no en `db.py`. Las summary queries por contrato van en `integrations/queries.py`.
- Solo lectura salvo `spi_builder` (único módulo que hace `INSERT`).

### Funciones de lectura de la Lambda — `db_reader.py`
`read_schedule(company_code)`, `read_payments(company_id)`, `read_last_dates(company_code, company_id)`.
Cada una abre y cierra su propia conexión, devuelve un `pd.DataFrame` (o dict de fechas) y convierte las
columnas de fecha con `pd.to_datetime(...).dt.date`.

### Inserts en batch — `spi_builder`
Un solo `cursor.executemany(_INSERT_SQL, rows)` por compañía, con `rows` como lista de dicts. Los errores por
contrato se acumulan y se loguean; si ninguna cuota se genera → `RuntimeError`.

## S3 — `s3_io.py`

- Cliente vía `boto3.client("s3")`. Paths con esquema `s3://bucket/key`, parseados por `_parse_s3_path`.
- **Formato según extensión**: `.parquet` → pyarrow; cualquier otra → CSV.
- `read_loan_tape(path)` falla si no existe; `try_read_loan_tape(path)` devuelve `None` ante `NoSuchKey`
  (se usa para el output previo y recuperar `dpd_max`).
- IO en memoria con `io.BytesIO` — no se escribe a disco.

## SNS — `sns_publisher.py` + `models.py`

- `publish_response(msg: OutboundMessage)` publica `json.dumps(msg.to_dict())` en `SNS_RESPONSE_TOPIC_ARN`.
- `origin` y `target` van **tanto en el body como en `MessageAttributes`** — el filtro de suscripción SNS→SQS
  los lee de los attributes. No los omitas.
- La **construcción** del mensaje vive en `models.py` (`OutboundMessage.from_inbound`), no en el publisher.

## Parseo de mensajes SQS

`InboundMessage.from_sqs_record(record)` parsea `record["body"]` (string JSON o dict). Las fechas se parsean con
`date.fromisoformat`. `MessageMetadata.to_dict()` **omite** campos None / con valor default (ej. `paid_threshold == 1.0`).

## Do / Don't

| ✅ Do | ❌ Don't |
|-------|---------|
| `conn.close()` en `finally` | Dejar conexiones abiertas |
| `commit`/`rollback` explícito en escrituras | Confiar en autocommit (está en False) |
| SQL junto a su consumidor | Meter SQL de negocio en `db.py` |
| `try_read_loan_tape` para el output previo | Asumir que el output previo siempre existe |
| `origin`/`target` en body **y** MessageAttributes | Publicar a SNS sin MessageAttributes |
