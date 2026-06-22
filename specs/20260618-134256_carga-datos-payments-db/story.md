**Created at**: 2026-06-18
**Status**: Done
**Original input**: @original_request.md
**Plan implemented**: @plan.md

# Story: Cargar los datos de cálculo desde payments_db (en vez de Excel), con resolución de compañía vía Company Provider

### Description
Hoy el pipeline de cálculo carga el schedule y el payment tape desde archivos Excel. Queremos que lea
directamente de `payments_db`: `load_schedule` desde `scheduled_payments_installments` y `load_payment_tape`
desde `payment_tape`, ambos **sanitizados**, y que `_payments_from_df` opere sobre el payment_tape sanitizado.
La compañía a filtrar se resuelve desde el mensaje SQS de entrada: el `borrower_id` se usa como `company_id`
(filtro de `payment_tape`), y el `company_code` (filtro de `installments`) se obtiene del servicio Company
Provider (mapea code ↔ id). Esto elimina la dependencia de archivos planos y alinea la carga con el flujo real
de datos en producción.

### Acceptance Criteria
- [ ] **Given** el identificador de compañía del SQS (`borrower_id`), **When** `load_payment_tape` carga los
  pagos, **Then** lee `payment_tape` filtrando por `company_id = borrower_id` y devuelve el DataFrame
  sanitizado con `sanitize_payment_tape`.
- [ ] **Given** el `company_code` resuelto vía Company Provider, **When** `load_schedule` carga el calendario,
  **Then** lee `scheduled_payments_installments` filtrando por `company_code` y devuelve el DataFrame sanitizado
  con `sanitize_schedule`.
- [ ] **Given** el payment_tape sanitizado, **When** `_payments_from_df` lo procesa, **Then** descarta filas
  inválidas (`payment_date` NaT o `total_payment <= 0`) y devuelve la lista de dicts; la sanitización se aplica
  a **ambas** tablas y no se omite en ningún caso.
- [ ] **Given** el `borrower_id`/identificador de compañía, **When** se resuelve la compañía, **Then** se usa el
  `CompanyClient` para obtener el `code` y se mapea a `company_code`; el `borrower_id` se usa como `company_id`,
  manteniendo el split documentado (numérico para `payment_tape`, string para `installments`).
- [ ] **Given** el cambio a `payments_db`, **When** corre el cálculo, **Then** ya no se leen archivos Excel para
  el schedule ni el payment tape (la lectura de archivos en estos loaders queda reemplazada).
- [ ] **Given** el `CompanyClient` recién agregado en `dpd/clients/`, **When** se integra al paquete, **Then**
  importa y funciona sin romper el resto de `dpd` (imports y configuración corregidos).

### Additional Context
**Funciones afectadas** (`dpd/excel_runner.py`): `load_schedule`, `load_payment_tape`, `_payments_from_df`
(y `_installments_from_df`, que consume el schedule sanitizado). Reutilizar el SQL/lectura ya existente en
`dpd/db_reader.py` (`read_schedule`/`read_payments`) y `dpd/integrations/db_excel_runner.py`
(`read_schedule`/`read_payment_tape`, que ya sanitizan) en lugar de duplicar queries; el plan decidirá cómo
consolidar. La conexión y credenciales de BD ya las resuelve `DBConfig.load()` (.env local / Secrets Manager en
Lambda), de la historia previa.

**Integración del Company Provider** (client agregado en `dpd/clients/`, copiado de `bancolombia_scrapper`).
Correcciones de paquete/config detectadas, necesarias para que importe y funcione:
- **Imports rotos a `dpd/utils/` (no existe):** `company_client.py` hace `from ..utils import secrets_manager`
  y `machine_to_machine.py` hace `from ..utils import aws_boto_session`, pero `aws_boto_session.py` está en
  `dpd/clients/`. Hay que crear `dpd/utils/` o corregir imports/ubicación.
- **Falta el helper** `secrets_manager.get_secret_value(key)` (DPD tiene `config._load_secret_values` y el
  módulo Terraform, pero no esa interfaz que el client espera, ej. `VAAS_HEADER`).
- **Constantes de config ausentes:** `dpd/config.py` es dataclass; el client usa constantes a nivel módulo que
  no existen: `COMPANY_API`, `M2M_TOKEN`, `AUTH0_CLIENT_ID_PARAM`, `AUTH0_CLIENT_SECRET_PARAM`, `AUTH0_AUDIENCE`,
  `AUTH0_ENDPOINT`, `LOCAL_ENV`, `AWS_PROFILE_NAME`.

**Dirección del mapeo a confirmar en el plan:** el SQS trae el `borrower_id` (numérico). `CompanyClient` hoy
expone `get_borrower_id_by_code(code) -> id` (code → id); para obtener `company_code` a partir del id puede hacer
falta el lookup inverso (id → code) en el servicio Company.

**Testing**: mockear la conexión a BD y el `CompanyClient`; verificar que ambos loaders sanitizan y filtran por
la compañía correcta, y que `_payments_from_df` descarta filas inválidas. Ver
[docs/testing/testing-guidelines.md](../../docs/testing/testing-guidelines.md).
