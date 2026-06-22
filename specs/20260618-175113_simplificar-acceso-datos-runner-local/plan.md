**Created at**: 2026-06-18
**Status**: Done
**Based on story**: @specs/20260618-175113_simplificar-acceso-datos-runner-local/story.md

# Plan: Simplificar acceso a datos eliminando CompanyClient y habilitar runner local

### Goal
Eliminar la dependencia de `CompanyClient` del flujo principal de la Lambda usando `company_id` directamente desde el evento SQS, actualizar todos los SQL de `scheduled_payments_installments` para filtrar por `company_id` (int) en lugar de `company_code` (str), y crear un runner local que permita emular la llegada de un evento sin depender del trigger SQS.

### Context
- `dpd/db_reader.py` — SQL y funciones de lectura que filtran por `company_code` → cambian a `company_id`
- `dpd/modes/cascade_fifo.py` — `INSTALLMENTS_SQL` filtra por `company_code`
- `dpd/modes/join_installment.py` — `SELECT_SQL` filtra por `company_code`
- `dpd/spi_builder.py` — `_INSERT_SQL` inserta `company_code` → cambia a `company_id`
- `dpd/config.py` — `RunConfig.company_code` se elimina
- `dpd/lambda_handler.py` — orquestador que hoy llama a `CompanyClient` para resolver `company_code`
- `dpd/clients/company_client.py` — se desacopla del flujo principal; header renombrado
- `dpd/local_runner.py` — nuevo punto de entrada local (aún no existe)
- `tests/test_consumers.py` — tests de cableado de la Lambda que mockean `CompanyClient`

### Public Contracts

**Services:**
```python
# db_reader.py — firma cambia
read_schedule(company_id: int, db_cfg=None) -> pd.DataFrame
read_last_dates(company_id: int, db_cfg=None) -> dict[str, Optional[date]]

# Nuevo CLI
# dpd/local_runner.py
main(argv: list[str] | None = None) -> int
# Uso: python -m dpd.local_runner --event evento.json
```

**Tests:**
- `tests/test_db_reader.py` — `test_read_schedule_filtra_por_company_id`
- `tests/test_consumers.py` — actualizar: quitar mocks de `CompanyClient`, agregar caso runner local

### Phases

#### Phase 1: Cambiar filtro SQL de company_code a company_id
Todos los SQL de `scheduled_payments_installments` usan `WHERE company_id = %(company_id)s`. `RunConfig.company_code` se elimina. `db_reader.read_schedule` y `read_last_dates` reciben `company_id: int`. Tests actualizados y pasando.
- [x] En `db_reader.py`: renombrar parámetro `company_code` → `company_id` en `SPI_LAST_DATE_SQL` y `read_last_dates()`
- [x] En `excel_runner.py`: cambiar `SCHEDULE_SQL` y `load_schedule()` a `company_id: int`
- [x] En `cascade_fifo.py`: cambiar `SCHEDULE_SQL` a `WHERE company_id = %(company_id)s`
- [x] En `join_installment.py`: cambiar `SCHEDULE_WITH_PAYMENTS_SQL` a `WHERE company_id = %(company_id)s`
- [x] En `spi_builder.py`: cambiar `_INSERT_SQL` y `build_and_persist` para usar `company_id`
- [x] En `config.py`: eliminar `company_code: str` de `RunConfig`
- [x] En `integrations/queries.py`, `integrations/db_excel_runner.py`, `products/dpd.py`: ajustar usos
- [x] Actualizar `tests/test_loaders.py` y `tests/test_consumers.py`
- [x] Correr tests y verificar que pasan (8/8 ✓)

#### Phase 2: Eliminar CompanyClient del flujo Lambda
`lambda_handler._process_message` usa `target_id` directamente como `company_id`. Se elimina el bloque de resolución vía API. Header renombrado a `VAAS_DAYS_PAST_DUE`.
- [x] En `lambda_handler.py`: eliminar import de `CompanyClient`, pasar `msg.target_id` como `company_id` directamente a `load_schedule`, `load_payment_tape` y `read_last_dates`
- [x] En `lambda_handler.py`: eliminar la lógica de resolución de `company_code` y el `RuntimeError` asociado
- [x] En `clients/company_client.py`: renombrar header `VAAS_BANCOLOMBIA_NEW_SCRAPPER` → `VAAS_DAYS_PAST_DUE`
- [x] Actualizar `tests/test_consumers.py`: flujo directo con `target_id`, sin mocks de `CompanyClient`
- [x] Correr tests y verificar que pasan (13/13 ✓)

#### Phase 3: Runner local
Nuevo `dpd/local_runner.py`: lee un JSON con la estructura del `InboundMessage`, construye el record SQS y llama `_process_message` directamente. Ejecutable como `python -m dpd.local_runner --event evento.json`.
- [x] Crear `dpd/local_runner.py` con `main()` y CLI (`--event`, `--dry-run`)
- [x] El runner construye `{"Records": [{"body": <contenido del JSON>}]}` y llama `lambda_handler.handler()`
- [x] Agregar `test_local_runner_procesa_evento_json` en `tests/test_consumers.py`
- [x] Correr tests y verificar que pasan (15/15 ✓)

### Next Step
All phases completed. See resume.md for the summary.
