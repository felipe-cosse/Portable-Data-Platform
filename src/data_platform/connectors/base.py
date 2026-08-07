from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import dlt
from dlt.destinations import clickhouse

from data_platform.config import ConfigurationError, SourceConfig


class BaseConnector(ABC):
    connector_type: ClassVar[str]
    _registry: ClassVar[dict[str, type[BaseConnector]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        connector_type = getattr(cls, "connector_type", None)
        if connector_type:
            BaseConnector._registry[connector_type] = cls

    def __init__(self, config: SourceConfig):
        self.config = config

    @abstractmethod
    def build_source(self) -> Any:
        """Build a dlt source, resource, or collection of resources."""

    def run(self) -> Any:
        credentials = {
            "host": os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            "port": int(os.getenv("CLICKHOUSE_PORT", "9000")),
            "http_port": int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123")),
            "database": os.getenv("CLICKHOUSE_DB", "analytics"),
            "username": os.getenv("CLICKHOUSE_USER", "platform"),
            "password": os.environ["CLICKHOUSE_PASSWORD"],
            "secure": int(os.getenv("CLICKHOUSE_SECURE", "0")),
        }
        destination = clickhouse(credentials=credentials)
        pipeline = dlt.pipeline(
            pipeline_name=f"ingest_{self.config.name}",
            destination=destination,
            dataset_name=self.config.dataset_name,
            pipelines_dir=os.getenv("DLT_PIPELINES_DIR", "/tmp/dlt"),
            progress=dlt.progress.log(dump_system_stats=False),
        )
        return pipeline.run(
            self.build_source(),
            write_disposition=self.config.write_disposition,
        )


def build_connector(config: SourceConfig) -> BaseConnector:
    connector_class = BaseConnector._registry.get(config.type)
    if connector_class is None:
        supported = ", ".join(sorted(BaseConnector._registry))
        raise ConfigurationError(
            f"Unsupported connector type {config.type!r}; supported types: {supported}"
        )
    return connector_class(config)
