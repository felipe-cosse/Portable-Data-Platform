#!/bin/sh
set -eu

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

: "${CLICKHOUSE_USER:?Set CLICKHOUSE_USER or load .env}"
: "${CLICKHOUSE_PASSWORD:?Set CLICKHOUSE_PASSWORD or load .env}"

curl --fail --silent --show-error \
  --user "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  "http://127.0.0.1:8123/?query=SELECT%201"
curl --fail --silent --show-error http://127.0.0.1:3000/server_info >/dev/null

echo
echo "ClickHouse and Dagster are responding."
