# Variables de entorno

Toda la configuración sensible se pasa por variables de entorno. Las de BD se **auto-cargan desde `.env`** en la
raíz del repo al importar `dpd.config` (ver `_load_dotenv` en [config.py](../../dpd/config.py)).

## Base de datos (MySQL)

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `DB_NAME` | **Sí** | — | Nombre de la base. `DBConfig.from_env()` falla si falta. |
| `DB_USER` | **Sí** | — | Usuario MySQL. Falla si falta. |
| `DB_HOST` | No | `localhost` | Host MySQL (en Lambda: endpoint dentro de la VPC). |
| `DB_PORT` | No | `3306` | Puerto MySQL. |
| `DB_PASSWORD` | No | `""` | Password MySQL. |

`DEFAULT_DBNAME = "payments_db"` en `db_excel_runner.py` se usa solo si no hay `DB_NAME` ni `--dbname`.

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
