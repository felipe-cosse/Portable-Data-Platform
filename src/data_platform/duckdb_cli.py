from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb


def _configure_s3(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("INSTALL httpfs")
    connection.execute("LOAD httpfs")
    settings = {
        "s3_region": os.getenv("AWS_DEFAULT_REGION"),
        "s3_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "s3_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "s3_session_token": os.getenv("AWS_SESSION_TOKEN"),
    }
    endpoint = os.getenv("S3_ENDPOINT_URL")
    if endpoint:
        settings["s3_endpoint"] = endpoint.removeprefix("http://").removeprefix("https://")
        settings["s3_url_style"] = "path"
        settings["s3_use_ssl"] = str(endpoint.startswith("https://")).lower()
    for name, value in settings.items():
        if value:
            connection.execute(f"SET {name} = ?", [value])


def register_file(
    connection: duckdb.DuckDBPyConnection,
    path: str,
    view_name: str = "source",
) -> None:
    if path.startswith("s3://"):
        _configure_s3(connection)

    normalized_path = path.lower().split("?", maxsplit=1)[0]
    if normalized_path.endswith((".csv", ".csv.gz")):
        relation = connection.read_csv(path, header=True, auto_detect=True)
    elif normalized_path.endswith((".json", ".jsonl", ".ndjson")):
        relation = connection.read_json(path, format="auto")
    elif normalized_path.endswith(".parquet") or "*" in path:
        relation = connection.from_parquet(path)
    else:
        raise ValueError(f"Cannot infer file type from path: {path}")
    relation.create_view(view_name, replace=True)


def query_file(path: str, sql: str) -> list[tuple[object, ...]]:
    with duckdb.connect() as connection:
        register_file(connection, path)
        return connection.execute(sql).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query CSV, JSON, JSONL, or Parquet with embedded DuckDB"
    )
    parser.add_argument("path", help="Local path, glob, or s3:// URL")
    parser.add_argument(
        "--sql",
        default="SELECT * FROM source LIMIT 20",
        help="SQL to execute; the input is registered as the source view",
    )
    args = parser.parse_args()

    if not args.path.startswith("s3://") and not any(
        character in args.path for character in "*?["
    ):
        path = Path(args.path)
        if not path.exists():
            parser.error(f"Path does not exist: {path}")

    with duckdb.connect() as connection:
        register_file(connection, args.path)
        connection.sql(args.sql).show(max_rows=100)


if __name__ == "__main__":
    main()
