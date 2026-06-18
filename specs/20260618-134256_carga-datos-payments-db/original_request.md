# Original request

> quiero cambiar la carga de los archivos por el uso de las tablas de payments_db. tenemos que remplazar la
> carga de los archivos por estas tablas: el load_schedule va a cargar la fila de tabla
> scheduled_payments_installments y para la funcion load_payment_tape se utilizara la tabla payment_tape
> tambien hay una funcion llamada _payments_from_df va a cargar los registros de la tabla payments

## Aclaraciones (rondas de preguntas)

- **Tabla "payments"**: es `payment_tape` pero **sanitizada**. La sanitización **no** se debe saltear: se aplica
  a **ambas** tablas (`scheduled_payments_installments` y `payment_tape`).
- **Excel vs BD**: se **reemplaza** la carga de Excel por lectura de `payments_db` (Excel deja de usarse en estos loaders).
- **Filtro de compañía**: viene del mensaje SQS de entrada.
  - `company_id` (filtro de `payment_tape`) = el `borrower_id` que llega en el SQS.
  - `company_code` (filtro de `scheduled_payments_installments`) = se obtiene llamando al **Company Provider**
    (client que dado el id devuelve id/nombre/**code**); se usa el `code` como `company_code`.

## Archivos del Company Provider (agregados por el usuario)

El usuario agregó el client en `dpd/clients/`:
- `dpd/clients/company_client.py` — `CompanyClient.get_borrower_id_by_code(code) -> id`
- `dpd/clients/machine_to_machine.py` — token M2M (Auth0 vía SSM)
- `dpd/clients/aws_boto_session.py` — sesión boto3

Copiados de `bancolombia_scrapper`; requieren corrección de paquetes/config para integrarse a DPD (ver
**Additional Context** en `story.md`).
