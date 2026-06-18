**Created at**: 2026-06-18
**Status**: Done
**Based on story**: @specs/20260618-182732_derivar-batch-loan-tape-umbral/story.md

# Plan: Derivar procesamiento a AWS Batch cuando el loan tape supera el umbral de registros

### Goal
Agregar en la Lambda la capacidad de detectar cuándo el loan tape supera un umbral configurable de registros y delegar el procesamiento a AWS Batch, evitando timeouts en portfolios grandes. La Lambda encola el job y retorna; el job de Batch ejecuta el mismo flujo y publica la respuesta en SNS.

### Context
- `dpd/config/config.py` — donde viven las constantes de módulo leídas del entorno; se agregan las 3 nuevas variables de Batch
- `dpd/lambda_handler.py` — orquestador principal; aquí se agrega el chequeo de umbral
- `.env.example` — actualizar con todas las variables del sistema incluyendo las nuevas
- `dpd/utils/aws_boto_session.py` — sesión boto3 a reutilizar para el cliente de AWS Batch
- `tests/test_consumers.py` — tests de cableado; se agregan los casos de derivación

### Public Contracts

**Services:**
```python
# dpd/config/config.py — nuevas constantes de módulo
BATCH_ROW_THRESHOLD: int   # int(os.environ.get("BATCH_ROW_THRESHOLD", "5000"))
BATCH_JOB_QUEUE: str       # os.environ.get("BATCH_JOB_QUEUE", "")
BATCH_JOB_DEFINITION: str  # os.environ.get("BATCH_JOB_DEFINITION", "")

# dpd/batch_submitter.py — nuevo módulo
def submit_job(payload: dict, queue: str, job_definition: str) -> str:
    """Encola un job en AWS Batch con el payload del evento. Retorna el jobId."""

# dpd/batch_handler.py — nuevo entry point para el job Batch
def main(argv: list[str] | None = None) -> int:
    # Lee el payload desde --payload <json_string> o variable de entorno DPD_BATCH_PAYLOAD
    # Ejecuta lambda_handler._process_message(msg) y retorna 0
```

**Tests:**
- `tests/test_consumers.py`:
  - `test_lambda_under_threshold_processes_inline` — loan tape con ≤ umbral → flujo normal, SNS publicado
  - `test_lambda_over_threshold_submits_batch` — loan tape con > umbral → `submit_job` llamado, SNS no publicado
  - `test_batch_handler_runs_process_message` — `batch_handler.main` parsea payload y llama `_process_message`

### Phases

#### Phase 1: Variables de entorno y .env.example
Agregar `BATCH_ROW_THRESHOLD`, `BATCH_JOB_QUEUE`, `BATCH_JOB_DEFINITION` en `config.py`. Actualizar `.env.example` con todas las variables del sistema. Tests verifican que las constantes cargan con los defaults correctos.
- [x] En `dpd/config/config.py`: agregar constantes `BATCH_ROW_THRESHOLD` (int, default 5000), `BATCH_JOB_QUEUE` (str, default ""), `BATCH_JOB_DEFINITION` (str, default "")
- [x] Actualizar `.env.example`: agregar sección AWS con `SNS_RESPONSE_TOPIC_ARN`, `PAYMENTS_SECRET_NAME`, `BATCH_ROW_THRESHOLD`, `BATCH_JOB_QUEUE`, `BATCH_JOB_DEFINITION`
- [x] Agregar `test_batch_config_defaults` en `tests/test_consumers.py`: verifica que las constantes tienen los valores default correctos cuando las env vars no están seteadas
- [x] Correr tests y verificar que pasan (11/11 ✓)

#### Phase 2: Derivación a Batch + batch_handler
Crear `dpd/batch_submitter.py` con `submit_job()`. Modificar `lambda_handler._process_message` para derivar al Batch cuando `len(loan_tape) > BATCH_ROW_THRESHOLD`. Crear `dpd/batch_handler.py` como entry point del job. Tests de ambas ramas y del handler.
- [x] Crear `dpd/batch_submitter.py` con `submit_job(payload, queue, job_definition)` usando `boto3.client("batch")`; validar que `queue` y `job_definition` no estén vacíos
- [x] En `lambda_handler._process_message`: después de leer el loan tape, si `len(loan_tape) > config.BATCH_ROW_THRESHOLD` → llamar `submit_job` y retornar sin publicar SNS
- [x] Crear `dpd/batch_handler.py`: lee payload desde `--payload` o `DPD_BATCH_PAYLOAD`; construye `InboundMessage` y llama `_process_message`
- [x] Agregar `test_lambda_under_threshold_processes_inline` en `tests/test_consumers.py`
- [x] Agregar `test_lambda_over_threshold_submits_batch` en `tests/test_consumers.py`
- [x] Agregar `test_batch_handler_runs_process_message` en `tests/test_consumers.py`
- [x] Correr tests y verificar que pasan (14/14 ✓)

### Next Step
All phases completed. See resume.md for the summary.
