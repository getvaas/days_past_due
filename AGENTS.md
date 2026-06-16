# AGENTS.md — Days Past Due (DPD) / Payments Expand

Índice de navegación para agentes. Cálculo de **morosidad (Days Past Due)** y productos derivados sobre el loan
tape de una compañía. Núcleo de cómputo puro (sin BD ni AWS) reutilizado desde 3 puntos de entrada: AWS Lambda
(SQS→SNS), Excel, y MySQL→Excel.

- **Stack:** Python 3.10+, pandas, PyMySQL, boto3, pyarrow, openpyxl. Sin ORM (SQL crudo). Dataclasses.
- **Idioma:** docstrings, comentarios y docs en **español**; nombres de código/SQL en inglés.

## Comandos clave

```bash
# Setup
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Correr DPD desde Excel (sin BD)
python -m dpd.excel_runner --schedule "tests/Days Past Due.xlsx" --payment-tape "tests/Days Past Due.xlsx" --mode cascade --out resultado_dpd.xlsx

# Correr DPD desde MySQL (solo lectura → Excel)
python -m dpd.integrations.db_excel_runner --company-id 86 --company-code sistecredito

# Tests (script aún no creado → /sdd.util.makeruntest). Smoke roto: ./tests/run.sh
./scripts/run-tests.sh
```

## Reglas de oro (no romper)

1. **`company_id` (numérico, payment_tape) ≠ `company_code` (string, installments)** — no se unen tablas por compañía.
2. **Dos fuentes de tasa de interés:** loan tape (`interest_rate`, para SPI) vs mensaje (`metadata.interest_rate`, para VPN). No mezclar.
3. **`Decimal`** para todo cálculo monetario en el núcleo. Nunca `float`.
4. **Lógica pura en `compute_from_data()`**; `compute(conn,...)` solo lee BD y delega.
5. **`dpd_max` nunca decrece** (high-watermark histórico vía output previo en S3).

## Routing — dónde mirar según la tarea

| Tema | Documentación |
|------|---------------|
| Arquitectura, capas, dependencias | [docs/architecture/architecture-principles.md](docs/architecture/architecture-principles.md) |
| Árbol de carpetas y responsabilidades | [docs/architecture/project-structure.md](docs/architecture/project-structure.md) |
| Términos de dominio (DPD, SPI, buckets…) | [docs/business/glossary.md](docs/business/glossary.md) |
| Modos de cálculo (join vs cascade) | [docs/business/calculation-modes.md](docs/business/calculation-modes.md) |
| Productos (dpd/total_amount/vpn) + generación de SPI | [docs/business/products.md](docs/business/products.md) |
| Estilo de código (Decimal, SQL, dataclasses) | [docs/code/code-style.md](docs/code/code-style.md) |
| Convenciones del núcleo de cómputo | [docs/code/compute-conventions.md](docs/code/compute-conventions.md) |
| Convenciones de acceso a datos (MySQL/S3/SNS) | [docs/code/data-access-conventions.md](docs/code/data-access-conventions.md) |
| Modelo de datos (tablas, ER) | [docs/database/data-model.md](docs/database/data-model.md) |
| Variables de entorno | [docs/configuration/environment-variables.md](docs/configuration/environment-variables.md) |
| Cómo correr cada entry point | [docs/how-to-run/execute.md](docs/how-to-run/execute.md) |
| Testing (estrategia, convenciones, runner) | [docs/testing/](docs/testing/) |

## AGENTS.md por subdirectorio

- [dpd/modes/AGENTS.md](dpd/modes/AGENTS.md) — modos de asignación de pagos.
- [dpd/products/AGENTS.md](dpd/products/AGENTS.md) — columnas derivadas del loan tape.
- [dpd/integrations/AGENTS.md](dpd/integrations/AGENTS.md) — acceso a MySQL y runner MySQL→Excel.
