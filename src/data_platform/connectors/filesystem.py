from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import dlt
import fsspec
from dlt.sources.filesystem import (
    filesystem,
    read_csv_duckdb,
    read_jsonl,
    read_parquet,
)

from data_platform.config import ConfigurationError
from data_platform.connectors.base import BaseConnector


def _select_path(payload: Any, path: str | None) -> Any:
    selected = payload
    if path:
        for component in path.split("."):
            if not isinstance(selected, dict) or component not in selected:
                raise ConfigurationError(f"JSON records_path does not exist: {path}")
            selected = selected[component]
    return selected


def _iter_json_records(
    pattern: str,
    storage_options: dict[str, Any],
    records_path: str | None,
) -> Iterator[dict[str, Any]]:
    for open_file in fsspec.open_files(pattern, mode="rt", **storage_options):
        with open_file as stream:
            selected = _select_path(json.load(stream), records_path)
        if isinstance(selected, list):
            for record in selected:
                if not isinstance(record, dict):
                    raise ConfigurationError("JSON arrays must contain objects")
                yield record
        elif isinstance(selected, dict):
            yield selected
        else:
            raise ConfigurationError("JSON input must resolve to an object or array of objects")


class FilesystemConnector(BaseConnector):
    connector_type = "filesystem"

    def _dlt_credentials(self) -> dict[str, Any] | None:
        credentials = self.config.options.get("credentials")
        if credentials is not None and not isinstance(credentials, dict):
            raise ConfigurationError(f"{self.config.name}.credentials must be a mapping")
        return credentials

    def _fsspec_storage_options(self) -> dict[str, Any]:
        credentials = self._dlt_credentials() or {}
        options: dict[str, Any] = {}
        key_map = {
            "aws_access_key_id": "key",
            "aws_secret_access_key": "secret",
            "aws_session_token": "token",
        }
        for source_key, destination_key in key_map.items():
            if credentials.get(source_key):
                options[destination_key] = credentials[source_key]
        if credentials.get("endpoint_url"):
            options["client_kwargs"] = {"endpoint_url": credentials["endpoint_url"]}
        return options

    def _json_resource(
        self,
        *,
        bucket_url: str,
        table_name: str,
        file_glob: str,
        records_path: str | None,
    ) -> Any:
        pattern = f"{bucket_url.rstrip('/')}/{file_glob.lstrip('/')}"
        storage_options = self._fsspec_storage_options()

        def records() -> Iterator[dict[str, Any]]:
            yield from _iter_json_records(pattern, storage_options, records_path)

        return dlt.resource(records, name=table_name)

    def build_source(self) -> list[Any]:
        bucket_url = self.config.options.get("bucket_url")
        tables = self.config.options.get("tables")
        if not isinstance(bucket_url, str) or not bucket_url:
            raise ConfigurationError(f"{self.config.name}.bucket_url is required")
        if not isinstance(tables, list) or not tables:
            raise ConfigurationError(f"{self.config.name}.tables must be a non-empty list")

        resources: list[Any] = []
        credentials = self._dlt_credentials()
        for table in tables:
            if not isinstance(table, dict):
                raise ConfigurationError(f"{self.config.name}.tables entries must be mappings")
            table_name = table.get("name")
            file_glob = table.get("file_glob")
            file_format = table.get("format")
            if not all(isinstance(value, str) and value for value in (table_name, file_glob)):
                raise ConfigurationError(
                    f"{self.config.name} table entries require name and file_glob"
                )

            if file_format == "json":
                resources.append(
                    self._json_resource(
                        bucket_url=bucket_url,
                        table_name=table_name,
                        file_glob=file_glob,
                        records_path=table.get("records_path"),
                    )
                )
                continue

            files_kwargs: dict[str, Any] = {
                "bucket_url": bucket_url,
                "file_glob": file_glob,
            }
            if credentials:
                files_kwargs["credentials"] = credentials
            files = filesystem(**files_kwargs)
            if file_format == "csv":
                reader = read_csv_duckdb()
            elif file_format == "jsonl":
                reader = read_jsonl()
            elif file_format == "parquet":
                reader = read_parquet()
            else:
                raise ConfigurationError(
                    f"{self.config.name}.{table_name} format must be csv, json, "
                    "jsonl, or parquet"
                )
            resources.append((files | reader).with_name(table_name))

        return resources
