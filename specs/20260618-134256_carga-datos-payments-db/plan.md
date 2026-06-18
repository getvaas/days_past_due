**Created at**: 2026-06-18
**Status**: Done
**Based on story**: @story.md

# Plan: Cargar datos de cálculo desde payments_db con resolución de compañía vía Company Provider

### Goal
Reemplazar la carga de Excel por lectura de `payments_db`: `load_schedule`/`load_payment_tape` (en
`excel_runner`) se vuelven los loaders canónicos que leen las tablas y las sanitizan, y la compañía se resuelve
desde el SQS (`target_id` → `company_id`; `CompanyClient.get_company_by_id` → `company_code`). Incluye integrar y
corregir el `CompanyClient` recién agregado.

### Context
- `dpd/excel_runner.py` — `load_schedule`/`load_payment_tape`/`_payments_from_df`/`_installments_from_df`; acá se reemplaza Excel por BD.
- `dpd/db_reader.py` — `SPI_SQL`/`PAYMENTS_SQL` + `read_schedule`/`read_payments`; fuente del SQL a reusar.
- `dpd/integrations/db.py` — `connect()`/`cursor()` (PyMySQL).
- `dpd/integrations/db_excel_runner.py` — `run_from_db`; consumidor a cablear.
- `dpd/lambda_handler.py` — `_process_message`; consumidor a cablear + resolución de compañía.
- `dpd/clients/{company_client,machine_to_machine,aws_boto_session}.py` — client agregado, con imports/config a corregir.
- `dpd/config.py` — agregar constantes a nivel módulo que el client espera.
- `docs/configuration/environment-variables.md`, `docs/database/data-model.md` — referencia.

### Public Contracts
- **Config** (`dpd/config.py`, constantes a nivel módulo desde env / `.env` ya cargado):
  - `COMPANY_API: str`, `AUTH0_CLIENT_ID_PARAM: str`, `AUTH0_CLIENT_SECRET_PARAM: str`, `AUTH0_AUDIENCE: str`, `AUTH0_ENDPOINT: str`, `AWS_PROFILE_NAME: str | None`
  - `LOCAL_ENV: bool = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None`
  - `M2M_TOKEN: str = ""` (cache mutable que setea `machine_to_machine.get_token`)
  - `VAAS_SECRET_NAME: str` (nombre del secret usado por el helper de secrets)
- **Utils** (`dpd/utils/`, paquete nuevo):
  - `dpd/utils/__init__.py`
  - `dpd/utils/aws_boto_session.py` — movido desde `dpd/clients/` (mismas funciones `get_session`/`get_*_client`).
  - `dpd/utils/secrets_manager.py` — `get_secret_value(key: str) -> str | None` (wrap boto3 Secrets Manager).
- **Clients** (`dpd/clients/`):
  - `machine_to_machine.py`: import → `from ..utils import aws_boto_session`.
  - `company_client.py`: import `from ..utils import secrets_manager` (ya existirá).
  - `CompanyClient.get_company_by_id(borrower_id: int) -> str | None` *(nuevo, id→code vía servicio Company)*.
  - `CompanyClient.get_borrower_id_by_code(code) -> int | None` — se mantiene.
- **Loaders** (`dpd/excel_runner.py`):
  - `load_schedule(company_code: str, db_cfg: DBConfig | None = None) -> pd.DataFrame` — lee `scheduled_payments_installments` (reusa `db_reader.SPI_SQL`) + `sanitize_schedule`.
  - `load_payment_tape(company_id: int, db_cfg: DBConfig | None = None) -> pd.DataFrame` — lee `payment_tape` (reusa `db_reader.PAYMENTS_SQL` / equivalente) + `sanitize_payment_tape`.
  - `_payments_from_df` / `_installments_from_df` — sin cambios.
  - **Removidos**: `_load_sheet`, `SCHEDULE_SHEET_FALLBACKS`, `PT_SHEET_FALLBACKS`, parámetros de path/sheet, `run_from_excel`, y el `main`/CLI basado en Excel. El rescate de columnas `Unnamed:` en `sanitize_payment_tape` (solo Excel) se simplifica.
- **Consumidores**:
  - `lambda_handler._process_message`: `company_id = msg.target_id`; `company_code = CompanyClient().get_company_by_id(msg.target_id)`; usar `load_schedule(company_code)` / `load_payment_tape(company_id)`.
  - `integrations/db_excel_runner.run_from_db`: usar los loaders canónicos; ajustar/retirar lo específico de Excel.
- **Tests** (`tests/`):
  - `tests/test_company_client.py`: `get_company_by_id` (requests mockeado) devuelve code; no encontrado → None; error HTTP → maneja/propaga.
  - `tests/test_loaders.py`: `load_schedule`/`load_payment_tape` con `connect`/`cursor` mockeados → df sanitizado correcto y filtrado por la compañía; `_payments_from_df` descarta `payment_date` NaT / `total_payment <= 0`.

### Phases

#### Phase 1: Integrar y corregir el CompanyClient
Dejar el client importable y funcional dentro de `dpd`.
- [x] Crear `dpd/utils/__init__.py`; mover `dpd/clients/aws_boto_session.py` → `dpd/utils/aws_boto_session.py`.
- [x] Crear `dpd/utils/secrets_manager.py` con `get_secret_value(key)` (boto3 Secrets Manager; usa `VAAS_SECRET_NAME`).
- [x] Agregar a `dpd/config.py` las constantes: `COMPANY_API`, `AUTH0_*`, `AWS_PROFILE_NAME`, `LOCAL_ENV`, `M2M_TOKEN`, `VAAS_SECRET_NAME`.
- [x] Corregir imports en `machine_to_machine.py` y `company_client.py` (ya apuntaban a `..utils`; resuelto al mover `aws_boto_session`).
- [x] Agregar `CompanyClient.get_company_by_id(borrower_id) -> str | None`. (+ `requests` agregado a `requirements.txt`.)
- [x] `tests/test_company_client.py` (requests + boto3 mockeados): 4 casos. Suite 18/18 verde (fallback `pytest`; Docker no disponible para `./scripts/run-tests.sh`).

#### Phase 2: Loaders BD canónicos en excel_runner
`load_schedule`/`load_payment_tape` leen `payments_db` y sanitizan; se retira Excel.
- [x] Reescribir `load_schedule(company_code, db_cfg=None)` y `load_payment_tape(company_id, db_cfg=None)` para leer BD + sanitizar (SQL `SELECT *` propio, compatible con los sanitizadores — el de `db_reader` aliasa `date`→`installment_date` y rompería `sanitize_schedule`).
- [x] Eliminar helpers/CLI de Excel (`_load_sheet`, fallbacks de hojas, `run_from_excel`, `main`, `_parse_date`); simplificar el rescate `Unnamed:` en `sanitize_payment_tape`.
- [x] `tests/test_loaders.py` (conexión mockeada): sanitización en ambas tablas, filtro por compañía, casos vacíos, `_payments_from_df` descarta inválidos. Suite 25/25 verde (fallback `pytest`; Docker no disponible).

#### Phase 3: Cablear consumidores + resolución de compañía
Lambda y CLI usan los loaders canónicos y resuelven la compañía desde el SQS.
- [x] `lambda_handler._process_message`: resolver `company_code` vía `CompanyClient().get_company_by_id(msg.target_id)`, `company_id = msg.target_id`, y usar `load_schedule`/`load_payment_tape`. (build_and_persist y read_last_dates usan el code/id resueltos.)
- [x] `integrations/db_excel_runner.run_from_db`: usa los loaders canónicos (`db_cfg=cfg`); removidos `read_schedule`/`read_payment_tape`, los SQL y `_PT_MIN_COLS` propios.
- [x] Actualizar `docs/` (`how-to-run/execute.md` sin entrada Excel + flujo Company Provider; `architecture/project-structure.md` con `clients/`, `utils/` y loaders BD).
- [x] `tests/test_consumers.py` (mocks): `_process_message` resuelve compañía y llama a los loaders; error si no hay code; `run_from_db` usa los loaders. Suite 28/28 verde (fallback `pytest`; Docker no disponible).

### Next Step
All phases completed. See resume.md for the summary.
