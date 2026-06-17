# Variables de entorno

Toda la configuración sensible se pasa por variables de entorno.

## Fuente de la config de BD según el entorno

`DBConfig.load()` ([config.py](../../dpd/config.py)) elige de dónde leer las credenciales:

- **Local** (sin `AWS_LAMBDA_FUNCTION_NAME`): `DBConfig.from_env()` → variables `DB_*`, auto-cargadas desde
  `.env` en la raíz del repo (ver `_load_dotenv`).
- **Lambda** (`AWS_LAMBDA_FUNCTION_NAME` presente, lo inyecta AWS): `DBConfig.from_secrets_manager()` → lee el
  secret indicado por `PAYMENTS_SECRET_NAME` desde AWS Secrets Manager y parsea su URL.

Los callers del flujo Lambda (`db_reader.py`, `spi_builder.py`) usan `DBConfig.load()`.
`integrations/db_excel_runner.py` es CLI solo local y sigue usando `from_env()`.

## Base de datos (MySQL) — solo local (`.env`)

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `DB_NAME` | **Sí** | — | Nombre de la base. `DBConfig.from_env()` falla si falta. |
| `DB_USER` | **Sí** | — | Usuario MySQL. Falla si falta. |
| `DB_HOST` | No | `localhost` | Host MySQL. |
| `DB_PORT` | No | `3306` | Puerto MySQL. |
| `DB_PASSWORD` | No | `""` | Password MySQL. |

`DEFAULT_DBNAME = "payments_db"` en `db_excel_runner.py` se usa solo si no hay `DB_NAME` ni `--dbname`.

## Base de datos (MySQL) — Lambda (Secrets Manager)

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `PAYMENTS_SECRET_NAME` | **Sí** (en Lambda) | Nombre/ARN del secret JSON con las credenciales de Payments. |

El secret debe tener las claves `DATASOURCE___PAYMENTS_DB___URL` (ej. `jdbc:mysql://host:3306/payments_db`),
`DATASOURCE___PAYMENTS_DB___USERNAME` y `DATASOURCE___PAYMENTS_DB___PASSWORD`. El rol de ejecución de la Lambda
necesita el permiso `secretsmanager:GetSecretValue` sobre ese secret. El secret se lee una sola vez por run (cacheado).

## AWS (solo Lambda)

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SNS_RESPONSE_TOPIC_ARN` | **Sí** (en Lambda) | ARN del SNS topic de respuesta. Lo lee `sns_publisher.publish_response`. |

Credenciales AWS: vía el rol de ejecución de la Lambda (boto3 las resuelve solo). En local, perfil/credenciales estándar de AWS.

## Comportamiento de `_load_dotenv`

- Lee `KEY=VALUE` línea por línea; ignora vacías y comentarios (`#`).
- **Pisa** valores ya presentes en el environment: el `.env` es la fuente de verdad para el entorno local
  (evita que un `source .env` previo en zsh deje credenciales corruptas con `$vars` expandidas).
- Quita comillas envolventes coincidentes (no recursivo).

## Setup local

```bash
cp .env.example .env   # y completá los valores
```

```
DB_HOST=
DB_PORT=3306
DB_NAME=
DB_USER=
DB_PASSWORD=
```

`.env` está en `.gitignore` — nunca se commitea. Ver [how-to-run/execute.md](../how-to-run/execute.md) para correr cada entry point.
