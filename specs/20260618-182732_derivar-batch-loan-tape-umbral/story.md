**Created at**: 2026-06-18
**Status**: Done
**Original input**: @specs/20260618-182732_derivar-batch-loan-tape-umbral/original_request.md
**Plan implemented**: @specs/20260618-182732_derivar-batch-loan-tape-umbral/plan.md

# Story: Derivar procesamiento a AWS Batch cuando el loan tape supera el umbral de registros

### Description
Cuando la Lambda lee el loan tape desde S3 y detecta que la cantidad de registros supera un umbral configurable (`BATCH_ROW_THRESHOLD`, default 5 000), debe delegar el procesamiento a AWS Batch en lugar de ejecutarlo inline. Esto evita timeouts de Lambda en portfolios grandes y permite escalar el cómputo sin cambiar el protocolo SQS/SNS. La Lambda termina sin publicar en SNS; el job de Batch ejecuta el mismo flujo de cálculo y publica la respuesta cuando finaliza.

### Acceptance Criteria
- [ ] **Given** un loan tape con registros ≤ `BATCH_ROW_THRESHOLD`, **When** la Lambda procesa el evento SQS, **Then** ejecuta el flujo inline actual y publica la respuesta en SNS sin cambios.
- [ ] **Given** un loan tape con registros > `BATCH_ROW_THRESHOLD`, **When** la Lambda procesa el evento SQS, **Then** envía un job a AWS Batch con el payload original del evento y retorna sin publicar en SNS.
- [ ] **Given** que el job de Batch fue encolado, **When** el job termina su ejecución, **Then** publica la respuesta en SNS con el mismo formato que el flujo Lambda actual.
- [ ] **Given** que `BATCH_ROW_THRESHOLD` no está definido, **When** la Lambda arranca, **Then** usa el default de 5 000 registros.
- [ ] **Given** que `BATCH_JOB_QUEUE` o `BATCH_JOB_DEFINITION` no están definidos al intentar encolar, **When** se supera el umbral, **Then** la Lambda lanza un error claro que identifica la variable faltante.
- [ ] El `.env.example` incluye todas las variables de entorno del sistema: `BATCH_ROW_THRESHOLD`, `BATCH_JOB_QUEUE`, `BATCH_JOB_DEFINITION`, `SNS_RESPONSE_TOPIC_ARN`, `PAYMENTS_SECRET_NAME`.

### Additional Context
- El job de Batch necesita un nuevo entry point `dpd/batch_handler.py` que recibe el payload del evento como argumento (JSON string o path a archivo) y ejecuta el mismo flujo que `lambda_handler._process_message`.
- Variables de entorno nuevas a agregar en `dpd/config.py` y `.env.example`:
  - `BATCH_ROW_THRESHOLD` — umbral de filas para derivar a Batch (int, default `5000`)
  - `BATCH_JOB_QUEUE` — nombre o ARN del job queue de AWS Batch
  - `BATCH_JOB_DEFINITION` — nombre o ARN de la job definition de AWS Batch
- Variables existentes que deben incorporarse al `.env.example` (hoy ausentes): `SNS_RESPONSE_TOPIC_ARN`, `PAYMENTS_SECRET_NAME`.
- El cliente de AWS Batch usará `boto3` con la misma sesión que el módulo `utils/aws_boto_session.py`.
- El flujo de Batch es idéntico al de Lambda: leer S3 → leer MySQL → calcular productos → escribir S3 → publicar SNS.
