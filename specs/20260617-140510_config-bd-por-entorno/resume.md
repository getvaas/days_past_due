**Created at**: 2026-06-17
**Based on plan**: @plan.md
**Based on story**: @story.md

# Resume: Resolver la configuración de BD según el entorno (.env en local, Secrets Manager en Lambda)

### Executive Summary
La app ahora elige automáticamente de dónde leer las credenciales de la base: en local sigue usando el `.env`,
y al correr en Lambda las obtiene de AWS Secrets Manager. Esto permite desplegar el mismo código sin manipular
credenciales a mano ni mantener un `.env` en la nube.

### Technical Summary
- `dpd/config.py`: nuevo `DBConfig.load()` que despacha por `AWS_LAMBDA_FUNCTION_NAME` (presente → Secrets
  Manager; ausente → `.env`/entorno). `from_env()` quedó intacto.
- `dpd/config.py`: nuevo `DBConfig.from_secrets_manager()` + helper `_parse_db_url()` (soporta
  `jdbc:mysql://` / `mysql://` / `host:port/db`, puerto default 3306, ignora query params).
- `dpd/config.py`: `_load_secret_values()` con `@lru_cache` → un solo `GetSecretValue` por run.
- Callers del flujo Lambda migrados a `DBConfig.load()`: `dpd/db_reader.py` (3 funciones) y `dpd/spi_builder.py`.
  `integrations/db_excel_runner.py` (CLI local) sin cambios.
- Nueva variable de entorno `PAYMENTS_SECRET_NAME` (nombre/ARN del secret); requiere permiso IAM
  `secretsmanager:GetSecretValue`. Documentado en `docs/configuration/environment-variables.md`.
- Tests: nuevo `tests/test_config.py` (14 casos: parser de URL, `from_secrets_manager` con boto3 mockeado,
  despacho de `load()`, cacheo). **14/14 verde** vía `pytest`.
- Nota de entorno: se instaló `boto3` (dependencia real, faltaba en el `.venv`) y `pytest` para verificar; el
  runner Docker `./scripts/run-tests.sh` aún no existe.

### Phases Completed
- [x] **Phase 1**: Resolución de `DBConfig` por entorno (núcleo) — `_parse_db_url`, `_load_secret_values` (cache),
  `from_secrets_manager` y `load()` en `config.py` + `tests/test_config.py` (14/14).
- [x] **Phase 2**: Cableado de callers + documentación — `db_reader.py` y `spi_builder.py` usan `load()`;
  `environment-variables.md` documenta `PAYMENTS_SECRET_NAME` y la selección de fuente por entorno.
