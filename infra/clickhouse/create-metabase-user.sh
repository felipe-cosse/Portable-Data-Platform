#!/bin/sh
set -eu

: "${CLICKHOUSE_DB:?CLICKHOUSE_DB is required}"
: "${CLICKHOUSE_USER:?CLICKHOUSE_USER is required}"
: "${CLICKHOUSE_PASSWORD:?CLICKHOUSE_PASSWORD is required}"
: "${METABASE_CLICKHOUSE_USER:?METABASE_CLICKHOUSE_USER is required}"
: "${METABASE_CLICKHOUSE_PASSWORD:?METABASE_CLICKHOUSE_PASSWORD is required}"

case "${CLICKHOUSE_DB}" in
  *[!A-Za-z0-9_]*)
    echo "CLICKHOUSE_DB must contain only letters, numbers, and underscores." >&2
    exit 1
    ;;
esac

case "${METABASE_CLICKHOUSE_USER}" in
  *[!A-Za-z0-9_]*)
    echo "METABASE_CLICKHOUSE_USER must contain only letters, numbers, and underscores." >&2
    exit 1
    ;;
esac

clickhouse-client \
  --host clickhouse \
  --user "${CLICKHOUSE_USER}" \
  --password "${CLICKHOUSE_PASSWORD}" \
  --param_metabase_user "${METABASE_CLICKHOUSE_USER}" \
  --param_metabase_password "${METABASE_CLICKHOUSE_PASSWORD}" \
  --query "
    CREATE USER IF NOT EXISTS {metabase_user:Identifier}
    IDENTIFIED WITH sha256_password BY {metabase_password:String}
  "

clickhouse-client \
  --host clickhouse \
  --user "${CLICKHOUSE_USER}" \
  --password "${CLICKHOUSE_PASSWORD}" \
  --param_metabase_user "${METABASE_CLICKHOUSE_USER}" \
  --param_metabase_password "${METABASE_CLICKHOUSE_PASSWORD}" \
  --query "
    ALTER USER {metabase_user:Identifier}
    IDENTIFIED WITH sha256_password BY {metabase_password:String}
  "

clickhouse-client \
  --host clickhouse \
  --user "${CLICKHOUSE_USER}" \
  --password "${CLICKHOUSE_PASSWORD}" \
  --query "
    GRANT SELECT ON \`${CLICKHOUSE_DB}\`.* TO \`${METABASE_CLICKHOUSE_USER}\`
  "

echo "Configured read-only ClickHouse access for Metabase."
