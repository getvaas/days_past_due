# AGENTS.md — dpd/integrations/

Acceso a **MySQL** y runner **MySQL→Excel (solo lectura)**.

- `db.py` — wrapper fino de PyMySQL (`connect`, `cursor`). SQL crudo, sin ORM.
- `queries.py` — summary queries por contrato (`current_dpd_by_contract`, `max_dpd_by_contract`).
- `db_excel_runner.py` — entry point: lee MySQL (solo lectura) y exporta DPD a Excel. Reusa `excel_runner.compute_dpd`.

## Antes de editar, leé

- Convenciones de acceso a datos (conexiones, SQL, commit/rollback): [../../docs/code/data-access-conventions.md](../../docs/code/data-access-conventions.md)
- Modelo de datos y filtros por compañía: [../../docs/database/data-model.md](../../docs/database/data-model.md)

## Reglas locales

- **SQL crudo, sin ORM.** Queries como constantes de módulo en MAYÚSCULAS, parámetros nombrados `%(x)s`.
- El SQL de negocio vive **junto a su consumidor**, no en `db.py`.
- Conexión: `connect()` con `autocommit=False`; cerrar en `finally`. Este paquete es **solo lectura** (los INSERT
  viven en `dpd/spi_builder.py`, fuera de acá).
- `db_excel_runner` filtra: `company_id` (numérico) en `payment_tape`, `company_code` (string) en installments.
  Hace `SELECT *` y deja que el sanitizador de `excel_runner` tome las columnas necesarias (portable a prod).
