# AGENTS.md — dpd/integrations/

Acceso a **MySQL** (wrapper de bajo nivel para PyMySQL).

- `db.py` — wrapper fino de PyMySQL: `connect`, `cursor`, y `connection` (conexión + cursor de solo lectura, cierra ambos). SQL crudo, sin ORM.

La lectura de las tablas de cálculo (`scheduled_payments_installments` / `payment_tape`) vive en
[../db_reader.py](../db_reader.py) (loaders que devuelven polars), no acá.

## Antes de editar, leé

- Convenciones de acceso a datos (conexiones, SQL, commit/rollback): [../../docs/code/data-access-conventions.md](../../docs/code/data-access-conventions.md)
- Modelo de datos y filtros por compañía: [../../docs/database/data-model.md](../../docs/database/data-model.md)

## Reglas locales

- **SQL crudo, sin ORM.** Queries como constantes de módulo en MAYÚSCULAS, parámetros nombrados `%(x)s`.
- El SQL de negocio vive **junto a su consumidor** (p.ej. en `db_reader`), no en `db.py`.
- Lectura: usar el context manager `connection(cfg)` (abre y cierra conexión + cursor). Para escritura con
  commit/rollback usar `connect()` + `cursor()` directo (los INSERT viven en `dpd/spi_builder.py`, fuera de acá).
