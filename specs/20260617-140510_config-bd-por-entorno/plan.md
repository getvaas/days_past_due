**Created at**: 2026-06-17
**Status**: Done
**Based on story**: @story.md

# Plan: Resolver la configuración de BD según el entorno (.env en local, Secrets Manager en Lambda)

### Goal
`DBConfig` elige automáticamente la fuente de credenciales según dónde corra: en local lee `.env`/entorno como
hoy, y en Lambda lee el secret de Payments desde AWS Secrets Manager (boto3), parseando su URL a host/puerto/base.
El secret se lee una sola vez por run.

### Context
- `dpd/config.py` — define `DBConfig` y `from_env()`; acá va el grueso del cambio (resolutor + loader de secret + parser de URL).
- `dpd/db_reader.py` — `read_schedule`/`read_payments`/`read_last_dates` hacen `db_cfg or DBConfig.from_env()`.
- `dpd/spi_builder.py` — `build_and_persist` hace `db_cfg or DBConfig.from_env()`.
- `dpd/integrations/db_excel_runner.py` — CLI solo local; queda sin cambios (referencia del comportamiento actual).
- `docs/configuration/environment-variables.md` — documentación de variables a actualizar.
- `docs/testing/test-conventions.md` — convenciones para `tests/test_config.py`.

### Public Contracts
- **Services** (`dpd/config.py`):
  - `DBConfig.from_env() -> DBConfig` — sin cambios (builder local desde `.env`/entorno).
  - `DBConfig.load() -> DBConfig` *(nuevo, classmethod)* — si `os.environ.get("AWS_LAMBDA_FUNCTION_NAME")` →
    `from_secrets_manager()`; si no → `from_env()`.
  - `DBConfig.from_secrets_manager(secret_name: str | None = None) -> DBConfig` *(nuevo, classmethod)* —
    `secret_name` default desde `os.environ["PAYMENTS_SECRET_NAME"]`; obtiene los valores (cacheados),
    extrae `DATASOURCE___PAYMENTS_DB___URL/USERNAME/PASSWORD` y parsea la URL.
  - `_load_secret_values(secret_name: str) -> dict` *(nuevo, módulo-level, `@lru_cache`)* — `boto3.client("secretsmanager").get_secret_value()` + `json.loads`; un solo `GetSecretValue` por `secret_name` por run.
  - `_parse_db_url(url: str) -> tuple[str, int, str]` *(nuevo, módulo-level)* — devuelve `(host, port, dbname)`;
    soporta `jdbc:mysql://host:port/db`, `mysql://host:port/db` y `host:port/db`; puerto default `3306`; ignora query params.
- **Tests** (`tests/test_config.py`, nuevo):
  - `_parse_db_url`: con esquema `jdbc:mysql://`, con `mysql://`, sin esquema, sin puerto (→3306), con query params (`?useSSL=false`), URL inválida (→ error).
  - `from_secrets_manager`: con boto3 mockeado arma el `DBConfig` correcto; falta `PAYMENTS_SECRET_NAME` → error; clave faltante en el JSON → error.
  - `load()`: con `AWS_LAMBDA_FUNCTION_NAME` seteado → usa Secrets Manager; sin él → usa `from_env()`.
  - Cache: dos llamadas a `from_secrets_manager()` en el mismo run → un solo `get_secret_value`.
- **Config / env vars**: nueva `PAYMENTS_SECRET_NAME` (nombre/ARN del secret de Payments). Documentar en `docs/configuration/environment-variables.md`.

### Phases

#### Phase 1: Resolución de `DBConfig` por entorno (núcleo)
Toda la lógica nueva en `config.py`, testeable sin red (boto3 mockeado).
- [x] Agregar `_parse_db_url(url)` en `dpd/config.py` (maneja esquemas `jdbc:mysql://`/`mysql://`/sin esquema, puerto default 3306, query params ignorados; URL inválida → `RuntimeError` claro).
- [x] Agregar `_load_secret_values(secret_name)` con `@lru_cache` (boto3 `secretsmanager.get_secret_value` + `json.loads`).
- [x] Agregar `DBConfig.from_secrets_manager(secret_name=None)` (default desde `PAYMENTS_SECRET_NAME`; extrae las 3 claves con error claro si falta alguna; arma `DBConfig` con el parser de URL).
- [x] Agregar `DBConfig.load()` que despacha por `AWS_LAMBDA_FUNCTION_NAME`.
- [x] Crear `tests/test_config.py` cubriendo parser, loader (boto3 mock), despacho y cache.
- [x] Correr la suite (fallback `pytest`: 14/14 verde; `./scripts/run-tests.sh` aún no existe).

#### Phase 2: Cableado de callers + documentación
Hacer que el flujo Lambda use el resolutor y dejar la doc al día.
- [x] Reemplazar `DBConfig.from_env()` por `DBConfig.load()` en `dpd/db_reader.py` (`read_schedule`, `read_payments`, `read_last_dates`).
- [x] Reemplazar `DBConfig.from_env()` por `DBConfig.load()` en `dpd/spi_builder.py` (`build_and_persist`).
- [x] Actualizar `docs/configuration/environment-variables.md`: agregar `PAYMENTS_SECRET_NAME`, documentar la selección de fuente por `AWS_LAMBDA_FUNCTION_NAME` y el permiso IAM `secretsmanager:GetSecretValue`.
- [x] Verificar que el camino local (sin `AWS_LAMBDA_FUNCTION_NAME`) sigue funcionando igual (imports OK + tests 14/14 verde; `db_excel_runner` sin cambios).

### Next Step
All phases completed. See resume.md for the summary.
