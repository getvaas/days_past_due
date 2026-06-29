# Estilo de código

Convenciones de Python que sigue todo el paquete `dpd/`. Basadas en el código existente, no aspiracionales.

## Reglas generales

- **`from __future__ import annotations`** como primera línea de import en **todos** los módulos.
- **Docstrings de módulo en español**, explicando el rol y (cuando aplica) las fórmulas. Ver `spi_builder.py`.
- **Type hints siempre.** Estilo moderno: `str | int`, `X | None`, `list[dict]`, `Optional[...]` para retornos.
- **snake_case** para funciones y variables; **PascalCase** para clases y dataclasses.
- Funciones helper privadas con prefijo `_` (`_load_sheet`, `_to_dec`, `_apply_pool_to_installment`).
- Comentarios y mensajes al usuario en español. Nombres de columnas/SQL/parámetros en inglés.

## Dinero y números

- **`Decimal` para todo cálculo monetario** en el núcleo (`modes/`, `spi_builder`). Nunca `float` en la lógica de mora.
- Convertí a `Decimal` vía `str()` para evitar imprecisión de floats que vienen de pandas/Excel:
  ```python
  def _to_dec(v) -> Decimal:
      if v is None:
          return Decimal(0)
      if isinstance(v, float) and v != v:  # NaN
          return Decimal(0)
      return Decimal(str(v))
  ```
- Redondeo monetario: `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.
- Los productos (`products/`) trabajan con pandas/float y redondean a 2 decimales en la salida.

## Dataclasses para estado estructurado

- Config y modelos son `@dataclass`. `RunConfig` y `DBConfig` son **`frozen=True`** (inmutables).
- Construcción desde fuentes externas vía classmethods: `DBConfig.from_env()`, `InboundMessage.from_sqs_record()`,
  `MessageMetadata.from_dict()`.
- Serialización vía `to_dict()` (ver `OutboundMessage`, `MessageMetadata`).

## SQL

- **SQL crudo, sin ORM.** Las queries son constantes de módulo en MAYÚSCULAS (`INSTALLMENTS_SQL`, `SPI_SQL`).
- **Siempre parámetros nombrados** `%(nombre)s` — nunca interpolación de strings:
  ```python
  cur.execute(SPI_SQL, {"company_code": str(company_code)})
  ```
- Usá el context manager `cursor(conn)` de `integrations/db.py` (devuelve `DictCursor` por default).

## Mensajes al usuario / logging

- **CLI local** (`local_runner`): `print()` con prefijo `⚠` para warnings. Resumen al final.
- **Lambda / Batch / librería** (`lambda_handler`, `batch_handler`, `processor`, `db_reader`, `modes/`): `logging`
  (`log = logging.getLogger(__name__)`). No mezclar `print()` en código de Lambda/Batch.

## Do / Don't

| ✅ Do | ❌ Don't |
|-------|---------|
| `Decimal(str(value))` en cálculo de mora | `float` para arrears o gross |
| Parámetros SQL nombrados `%(x)s` | f-strings dentro del SQL |
| Lógica pura en `compute_from_data()` | Lógica de negocio dentro de `compute(conn, ...)` |
| `logging` en Lambda, `print` en CLI | `print` en `lambda_handler` |
| `frozen=True` en config | mutar `RunConfig`/`DBConfig` |

Convenciones por capa: [compute-conventions.md](compute-conventions.md) y
[data-access-conventions.md](data-access-conventions.md).
