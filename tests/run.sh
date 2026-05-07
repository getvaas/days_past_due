#!/usr/bin/env bash
# Integration smoke test for the DPD job against a throwaway MySQL.
#
# Usage:
#   ./tests/run.sh join             # Mode 1
#   ./tests/run.sh cascade          # Mode 2 sin partial-counts
#   ./tests/run.sh cascade --partial-counts
#
# Asume docker disponible. Levanta un contenedor 'dpd-mysql', aplica schema+seed,
# corre el job, e imprime el verify. El contenedor queda corriendo para que
# puedas iterar; bórralo con: docker rm -f dpd-mysql

set -euo pipefail

MODE="${1:-join}"; shift || true
EXTRA_ARGS=("$@")

CONTAINER="dpd-mysql"
DB_NAME_TEST="dpd_test"
DB_USER_TEST="root"
DB_PASS_TEST="test"
DB_PORT_TEST="${TEST_DB_PORT:-3307}"   # 3307 para no chocar con MySQL local en 3306
CALC_DATE="2026-05-04"

cd "$(dirname "$0")/.."

echo "==> MySQL container ($CONTAINER on :$DB_PORT_TEST)"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        docker start "$CONTAINER" >/dev/null
    else
        docker run -d --name "$CONTAINER" \
            -e MYSQL_ROOT_PASSWORD="$DB_PASS_TEST" \
            -e MYSQL_DATABASE="$DB_NAME_TEST" \
            -p "${DB_PORT_TEST}:3306" \
            mysql:8 >/dev/null
    fi
fi

echo "==> Esperando a que MySQL acepte conexiones"
until docker exec "$CONTAINER" mysqladmin ping -h 127.0.0.1 -uroot -p"$DB_PASS_TEST" --silent >/dev/null 2>&1; do
    sleep 1
done

echo "==> Aplicando schema + seed"
docker exec -i "$CONTAINER" mysql -uroot -p"$DB_PASS_TEST" "$DB_NAME_TEST" < tests/schema.sql
docker exec -i "$CONTAINER" mysql -uroot -p"$DB_PASS_TEST" "$DB_NAME_TEST" < tests/seed.sql

echo "==> Corriendo el job (mode=$MODE date=$CALC_DATE ${EXTRA_ARGS[*]:-})"
export DB_HOST=127.0.0.1
export DB_PORT="$DB_PORT_TEST"
export DB_NAME="$DB_NAME_TEST"
export DB_USER="$DB_USER_TEST"
export DB_PASSWORD="$DB_PASS_TEST"

python -m dpd.main \
    --company-id 42 \
    --company-code 42 \
    --mode "$MODE" \
    --date "$CALC_DATE" \
    "${EXTRA_ARGS[@]}"

echo
echo "==> Resultado por cuota (verify.sql)"
docker exec -i "$CONTAINER" mysql -uroot -p"$DB_PASS_TEST" -t "$DB_NAME_TEST" < tests/verify.sql
