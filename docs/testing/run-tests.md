# Cómo correr los tests

## Método principal (configurado)

El proyecto define el runner de tests en `.sdd.json` → `paths.run_tests`:

```bash
./scripts/run-tests.sh
```

Este script está pensado para correr los tests dentro de **Docker**, garantizando resultados consistentes y
reproducibles sin depender de las dependencias del host.

> ⚠ **El script aún NO existe.** `./scripts/run-tests.sh` no está creado todavía. Para generarlo (adaptado al
> stack Python de este proyecto), ejecutá:
>
> ```
> /sdd.util.makeruntest
> ```
>
> Esto crea `scripts/run-tests.sh` y `scripts/clean-test-cache.sh` (este último también configurado en
> `paths.clean_test_cache`).

## Fallback — solo para debugging local rápido

> No usar en flujos de implementación; el método oficial es el script Docker de arriba.

Una vez que existan tests unitarios (ver [testing-guidelines.md](testing-guidelines.md)):

```bash
source .venv/bin/activate
python -m pytest tests/ -v          # si se adopta pytest
```

## Smoke test de integración existente (⚠ roto)

Hay un smoke test contra un MySQL descartable en [tests/run.sh](../../tests/run.sh):

```bash
./tests/run.sh join                      # Modo 1
./tests/run.sh cascade                   # Modo 2
./tests/run.sh cascade --partial-counts
```

Levanta un contenedor `dpd-mysql`, aplica `tests/schema.sql` + `tests/seed.sql`, corre el job e imprime
`tests/verify.sql`. Borralo con `docker rm -f dpd-mysql`.

**Está roto**: invoca `python -m dpd.main`, un entry point eliminado en el refactor a `integrations/`. Hasta
arreglarlo, para correr DPD contra MySQL usar `python -m dpd.integrations.db_excel_runner` (ver
[how-to-run/execute.md](../how-to-run/execute.md)). Arreglarlo implica apuntar `run.sh` al runner vigente.
