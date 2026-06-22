**Created at**: 2026-06-18
**Status**: Done
**Original input**: @specs/20260618-175113_simplificar-acceso-datos-runner-local/original_request.md
**Plan implemented**: @specs/20260618-175113_simplificar-acceso-datos-runner-local/plan.md

# Story: Simplificar acceso a datos eliminando CompanyClient y habilitar runner local

### Description
Actualmente la Lambda resuelve el `company_code` llamando a un servicio externo (`CompanyClient`) antes de poder leer `scheduled_payments_installments`. Dado que esa tabla ahora tiene una columna `company_id` (int), la resolución externa ya no es necesaria — el `company_id` llega directamente en el evento SQS. Adicionalmente, se necesita un runner local que permita emular la llegada de un evento sin depender del trigger SQS, facilitando el desarrollo y el debugging. Como parte del orden previo, se unificaron los módulos S3 en `utils/s3.py` y se eliminó `s3_io.py`.

### Acceptance Criteria
- [ ] **Given** un evento SQS con `target_id` (company_id), **When** la Lambda procesa el mensaje, **Then** lee `scheduled_payments_installments` filtrando por `company_id` sin llamar a `CompanyClient` ni a ningún servicio externo.
- [ ] **Given** que `CompanyClient` y `machine_to_machine` ya no son usados por la Lambda, **When** se revisa el código, **Then** esos módulos están desacoplados del flujo principal (pueden eliminarse o quedar inactivos sin romper nada).
- [ ] **Given** un archivo JSON local con la estructura del mensaje SQS (`input_file`, `output_file`, `products`, `target_id`, etc.), **When** se ejecuta el runner local (`python -m dpd.local_runner --event evento.json`), **Then** se ejecuta el mismo flujo que la Lambda: descarga loan tape de S3, procesa, sube el CSV enriquecido a S3.
- [ ] **Given** que el header `X-User-Id` en `company_client.py` tiene el valor `VAAS_BANCOLOMBIA_NEW_SCRAPPER`, **When** se refactoriza el módulo, **Then** el valor refleja el identificador propio de este servicio (`VAAS_DAYS_PAST_DUE`).
- [ ] **Given** el filtro de `scheduled_payments_installments` cambia de `company_code` a `company_id`, **When** se revisan los SQL en `db_reader.py`, `cascade_fifo.py` y `join_installment.py`, **Then** todos usan `WHERE company_id = %(company_id)s` (int) en lugar de `WHERE company_code = %(company_code)s` (string).
- [ ] **Given** los cambios anteriores, **When** se corren los tests existentes, **Then** todos pasan sin modificar la lógica de negocio de cálculo DPD.

### Additional Context
- `company_id` es el identificador numérico que ya viene en `target_id` del mensaje SQS — no requiere transformación.
- `RunConfig.company_code` puede eliminarse o dejarse como campo opcional sin uso activo; decisión del implementador según impacto en tests.
- El runner local usa las mismas credenciales AWS del entorno (perfil configurado en `AWS_PROFILE_NAME` o variables de entorno) — no requiere mocking de S3.
- El flujo del runner local es idéntico al de la Lambda: `InboundMessage.from_sqs_record` → `_process_message`. La diferencia es solo cómo llega el evento (JSON en disco vs SQS).
- `utils/s3.py` ya está unificado (refactor previo en esta rama): reemplaza a `s3_io.py` con soporte de perfil AWS local.
