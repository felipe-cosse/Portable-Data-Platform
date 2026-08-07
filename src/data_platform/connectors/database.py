from __future__ import annotations

import os
from typing import Any

from dlt.sources.sql_database import sql_database

from data_platform.config import ConfigurationError
from data_platform.connectors.base import BaseConnector


class DatabaseConnector(BaseConnector):
    connector_type = "database"

    def build_source(self) -> Any:
        engine = self.config.options.get("engine")
        if engine not in {"postgresql", "mysql"}:
            raise ConfigurationError(
                f"{self.config.name}.engine must be postgresql or mysql"
            )

        credentials_env = self.config.options.get("credentials_env")
        if not isinstance(credentials_env, str) or not credentials_env:
            raise ConfigurationError(f"{self.config.name}.credentials_env is required")
        try:
            credentials = os.environ[credentials_env]
        except KeyError as error:
            raise ConfigurationError(
                f"Missing database credential environment variable: {credentials_env}"
            ) from error

        table_names = self.config.options.get("table_names")
        if not isinstance(table_names, list) or not table_names:
            raise ConfigurationError(f"{self.config.name}.table_names must be a non-empty list")

        return sql_database(
            credentials=credentials,
            schema=self.config.options.get("schema"),
            table_names=table_names,
            chunk_size=int(self.config.options.get("chunk_size", 50_000)),
            backend=self.config.options.get("backend", "pyarrow"),
            include_views=bool(self.config.options.get("include_views", False)),
        )
