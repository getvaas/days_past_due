**Created at**: 2026-06-17
**Status**: Done
**Original input**: @original_request.md
**Plan implemented**: @plan.md

# Story: Resolver la configuración de BD según el entorno: `.env` en local, Secrets Manager en Lambda

### Description
Hoy `DBConfig` siempre carga las credenciales de MySQL desde el `.env` de la raíz del repo. En entornos
desplegados (Lambda) no existe `.env` y las credenciales viven en AWS Secrets Manager. Necesitamos que la app
elija la fuente de configuración automáticamente según dónde corra, de modo que el mismo código funcione en
local y en la nube sin manipular credenciales ni cambiar el flujo de ejecución.

### Acceptance Criteria
- [ ] **Given** una ejecución local (sin la variable `AWS_LAMBDA_FUNCTION_NAME`), **When** se resuelve la
  configuración de BD, **Then** se construye `DBConfig` con las variables `DB_*` del entorno/`.env`, igual que
  hoy (comportamiento actual intacto).
- [ ] **Given** una ejecución en Lambda (`AWS_LAMBDA_FUNCTION_NAME` presente), **When** se resuelve la
  configuración de BD, **Then** se lee el secret indicado por la variable de entorno del nombre/ARN del secret
  (ej. `PAYMENTS_SECRET_NAME`) desde Secrets Manager con boto3 y se construye `DBConfig` a partir de su JSON.
- [ ] **Given** un secret con `DATASOURCE___PAYMENTS_DB___URL`, `DATASOURCE___PAYMENTS_DB___USERNAME` y
  `DATASOURCE___PAYMENTS_DB___PASSWORD`, **When** se parsea, **Then** la URL se descompone en host / puerto /
  nombre de base (puerto por defecto `3306` si la URL no lo trae), `USERNAME` → `user` y `PASSWORD` → `password`.
- [ ] **Given** una URL con esquema `jdbc:mysql://...` o `mysql://...` y/o parámetros de query (ej.
  `?useSSL=false`), **When** se parsea, **Then** se ignoran el esquema y los parámetros y se extraen
  host/puerto/base correctamente.
- [ ] **Given** una ejecución en Lambda sin el nombre del secret, o con el secret/claves ausentes, o con una URL
  no parseable, **When** se resuelve la configuración, **Then** se lanza un error claro que indica exactamente
  qué falta (sin caer silenciosamente al `.env`).
- [ ] **Given** un mismo run que abre varias conexiones (ej. `read_schedule` + `read_payments` +
  `read_last_dates`), **When** se resuelve la configuración más de una vez, **Then** el secret se lee **una sola
  vez** (resultado cacheado) y no se repite `GetSecretValue` por cada conexión.

### Additional Context
- **Punto de cambio**: `dpd/config.py`. Introducir un resolutor único (ej. `DBConfig.load()`) que despache por la
  presencia de `AWS_LAMBDA_FUNCTION_NAME`: ausente → `DBConfig.from_env()` (builder local actual, sin cambios);
  presente → nuevo `DBConfig.from_secrets_manager()`. Actualizar los callers que hoy hacen
  `db_cfg or DBConfig.from_env()` en `dpd/db_reader.py` y `dpd/spi_builder.py` para que usen el resolutor.
  `dpd/integrations/db_excel_runner.py` es una CLI **solo local** → puede seguir usando `from_env()`.
- `from_secrets_manager()` usa `boto3.client("secretsmanager")` (la región la resuelve el entorno de la Lambda)
  y `json.loads` sobre el `SecretString`. El nombre/ARN del secret llega por env var.
- **Permiso IAM**: el rol de ejecución debe incluir `secretsmanager:GetSecretValue` sobre el secret de Payments
  (ver `original_request.md`). Es requisito de infraestructura, no de este código.
- `_load_dotenv` corre al importar `dpd.config`; en Lambda no hay `.env`, así que es un no-op y no interfiere.
- boto3 ya está en `requirements.txt`.
- **Testing** (núcleo, sin red): mockear el cliente de Secrets Manager para cubrir `from_secrets_manager()`,
  el parseo de la URL (con/ sin esquema, con/sin puerto, con query params) y el despacho por
  `AWS_LAMBDA_FUNCTION_NAME`. Ver [docs/testing/testing-guidelines.md](../../docs/testing/testing-guidelines.md).
- **Nota de entorno**: la detección asume runtime **Lambda** (`AWS_LAMBDA_FUNCTION_NAME`). Si en el futuro el
  servicio corre también en ECS/contenedor fuera de Lambda, esa variable no estará y se trataría como "local";
  habría que revisar el criterio de detección.
