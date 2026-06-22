# Original Request

## Fuente
Conversación directa — 2026-06-18

## Contexto acumulado en la sesión

1. **Header del token hardcodeado con nombre de otro proyecto**
   `company_client.py` tiene `"X-User-Id": "VAAS_BANCOLOMBIA_NEW_SCRAPPER"` — es un remanente del scrapper de Bancolombia y debe renombrarse a `VAAS_DAYS_PAST_DUE`.

2. **Eliminar CompanyClient**
   `scheduled_payments_installments` ahora tiene columna `company_id` (int). Ya no es necesario resolver el `company_code` vía API externa. El `company_id` llega directo en el campo `target_id` del evento SQS. Esto implica cambiar el filtro SQL en `db_reader`, `cascade_fifo` y `join_installment`.

3. **Runner local para emular evento SQS**
   Se necesita ejecutar el flujo de la Lambda localmente sin depender del trigger SQS. El runner acepta un JSON con la misma estructura del mensaje de entrada (`InboundMessage`) y ejecuta `_process_message` directamente. La conexión a S3 usa las credenciales AWS ya configuradas (no hay mocking).

4. **Refactor S3 previo (ya aplicado en esta sesión)**
   - `dpd/s3_io.py` eliminado.
   - `dpd/utils/s3.py` unificado: contiene `read_loan_tape`, `try_read_loan_tape`, `write_loan_tape` (con soporte de perfil AWS) y `upload_string`.
   - `lambda_handler.py` actualizado para importar desde `utils.s3`.
