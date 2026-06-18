**Created at**: 2026-06-18
**Based on plan**: @specs/20260618-182732_derivar-batch-loan-tape-umbral/plan.md
**Based on story**: @specs/20260618-182732_derivar-batch-loan-tape-umbral/story.md

# Resume: Derivar procesamiento a AWS Batch cuando el loan tape supera el umbral de registros

### Executive Summary
La Lambda ahora detecta automáticamente cuando el loan tape supera un umbral configurable (`BATCH_ROW_THRESHOLD`, default 5 000 filas) y delega el procesamiento a AWS Batch en lugar de ejecutarlo inline, evitando timeouts en portfolios grandes. Se creó un entry point de Batch (`batch_handler.py`) que reproduce el mismo flujo de cálculo y publica la respuesta en SNS al finalizar. El `.env.example` fue completado con todas las variables del sistema.

### Technical Summary
- `dpd/config/config.py`: nuevas constantes `BATCH_ROW_THRESHOLD` (int, default 5000), `BATCH_JOB_QUEUE`, `BATCH_JOB_DEFINITION`; re-exportadas desde `dpd/config/__init__.py`
- `dpd/batch_submitter.py`: nuevo módulo con `submit_job(payload, queue, job_definition)` vía `boto3.client("batch")`; valida variables vacías con `ValueError` claro
- `dpd/lambda_handler.py`: chequeo de umbral después de leer el loan tape — si supera el límite, encola en Batch y retorna sin publicar SNS
- `dpd/batch_handler.py`: nuevo entry point CLI para el job de Batch; lee payload desde `--payload` o `DPD_BATCH_PAYLOAD` y ejecuta `_process_message`
- `.env.example`: completado con todas las variables (`DB_*`, `SNS_RESPONSE_TOPIC_ARN`, `PAYMENTS_SECRET_NAME`, `BATCH_*`, `AWS_PROFILE_NAME`)
- 14 tests pasando (3 nuevos para los flujos inline, derivado y batch handler)

### Phases Completed
- [x] **Phase 1**: Variables de entorno y .env.example — constantes de Batch en `config.py`, `.env.example` completo, test de defaults ✓
- [x] **Phase 2**: Derivación a Batch + batch_handler — `batch_submitter.py`, lógica de derivación en `lambda_handler`, `batch_handler.py` y 3 tests de cableado ✓
