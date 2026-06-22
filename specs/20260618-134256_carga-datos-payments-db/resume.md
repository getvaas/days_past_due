**Created at**: 2026-06-18
**Based on plan**: @plan.md
**Based on story**: @story.md

# Resume: Cargar datos de cálculo desde payments_db con resolución de compañía vía Company Provider

### Executive Summary
DPD ahora lee el calendario de cuotas y los pagos directamente de `payments_db` en vez de archivos Excel, y
resuelve la compañía a partir del mensaje SQS de entrada. Esto alinea el cálculo con el flujo real de
producción y elimina la dependencia de archivos planos.

### Technical Summary
- `dpd/utils/` (paquete nuevo): `aws_boto_session` (movido desde `clients/`) y `secrets_manager.get_secret_value`.
- `dpd/config.py`: constantes a nivel módulo para los clients (`COMPANY_API`, `AUTH0_*`, `AWS_PROFILE_NAME`,
  `VAAS_SECRET_NAME`, `LOCAL_ENV`, `M2M_TOKEN`).
- `dpd/clients/company_client.py`: nuevo `get_company_by_id(borrower_id) -> code` (id→code); imports de los
  clients resueltos al mover `aws_boto_session` a `utils/`.
- `dpd/excel_runner.py`: `load_schedule(company_code)` y `load_payment_tape(company_id)` ahora leen `payments_db`
  (SELECT * + sanitización); **removidos** `run_from_excel`, `_load_sheet`, los `*_SHEET_FALLBACKS`, la CLI de
  Excel y el rescate `Unnamed:`. `compute_dpd`/`export_results`/sanitizadores/converters intactos.
- `dpd/lambda_handler.py`: resuelve `company_id = target_id` y `company_code` vía `CompanyClient`, y usa los
  loaders canónicos (en lugar de `db_reader.read_schedule`/`read_payments`).
- `dpd/integrations/db_excel_runner.py`: `run_from_db` usa los loaders canónicos; removidos sus read/SQL propios.
- `requirements.txt`: agregado `requests` (clients HTTP).
- Docs actualizadas: `how-to-run/execute.md`, `architecture/project-structure.md`.
- Tests: `tests/test_company_client.py`, `tests/test_loaders.py`, `tests/test_consumers.py`. **Suite 28/28 verde**
  (fallback `pytest`; el runner Docker `./scripts/run-tests.sh` no se pudo ejecutar por falta de Docker activo).

### Phases Completed
- [x] **Phase 1**: Integrar y corregir el CompanyClient — `dpd/utils/`, constantes de config, imports, `get_company_by_id`.
- [x] **Phase 2**: Loaders BD canónicos en `excel_runner` — `load_schedule`/`load_payment_tape` leen `payments_db` + sanitizan; retirado Excel.
- [x] **Phase 3**: Cablear `lambda_handler` y `db_excel_runner` a los loaders + resolución de compañía vía Company Provider; docs.
