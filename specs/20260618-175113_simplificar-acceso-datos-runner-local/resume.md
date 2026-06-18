**Created at**: 2026-06-18
**Based on plan**: @specs/20260618-175113_simplificar-acceso-datos-runner-local/plan.md
**Based on story**: @specs/20260618-175113_simplificar-acceso-datos-runner-local/story.md

# Resume: Simplificar acceso a datos y habilitar runner local

### Executive Summary
Se eliminó la dependencia de `CompanyClient` del flujo principal de la Lambda: ahora `company_id` se toma directamente del evento SQS, eliminando una llamada HTTP a una API externa en cada ejecución. Se unificaron los módulos S3, se actualizaron todos los SQL para filtrar por `company_id` (int), y se creó un runner local que permite ejecutar el flujo completo de la Lambda sin necesitar un trigger SQS real.

### Technical Summary
- `dpd/s3_io.py` eliminado; funcionalidad unificada en `dpd/utils/s3.py` con soporte de perfil AWS local vía `aws_boto_session`
- `RunConfig.company_code: str` eliminado; todos los SQL usan `WHERE company_id = %(company_id)s` (int)
- `lambda_handler._process_message`: eliminado bloque de resolución via `CompanyClient`; `company_id = msg.target_id` directo
- `dpd/clients/company_client.py`: header renombrado de `VAAS_BANCOLOMBIA_NEW_SCRAPPER` → `VAAS_DAYS_PAST_DUE`
- Archivos afectados: `db_reader.py`, `excel_runner.py`, `cascade_fifo.py`, `join_installment.py`, `spi_builder.py`, `config.py`, `integrations/queries.py`, `integrations/db_excel_runner.py`, `products/dpd.py`
- `dpd/local_runner.py` creado: CLI `python -m dpd.local_runner --event evento.json [--dry-run]`
- 15 tests pasando (sin mocks de `CompanyClient`)

### Phases Completed
- [x] **Phase 1**: Cambiar filtro SQL de company_code a company_id — todos los SQL y firmas de funciones actualizados; `RunConfig.company_code` eliminado; 8/8 tests ✓
- [x] **Phase 2**: Eliminar CompanyClient del flujo Lambda — `_process_message` usa `target_id` directamente; header renombrado; 13/13 tests ✓
- [x] **Phase 3**: Runner local — `dpd/local_runner.py` creado con `--event` y `--dry-run`; 15/15 tests ✓
