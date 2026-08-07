from __future__ import annotations

from typing import Any

from dlt.sources.rest_api import rest_api_source

from data_platform.config import ConfigurationError
from data_platform.connectors.base import BaseConnector


class ApiConnector(BaseConnector):
    connector_type = "api"

    def build_source(self) -> Any:
        base_url = self.config.options.get("base_url")
        resources = self.config.options.get("resources")
        if not isinstance(base_url, str) or not base_url:
            raise ConfigurationError(f"{self.config.name}.base_url is required")
        if not isinstance(resources, list) or not resources:
            raise ConfigurationError(f"{self.config.name}.resources must be a non-empty list")

        client: dict[str, Any] = {"base_url": base_url}
        for optional_key in ("headers", "auth", "paginator"):
            value = self.config.options.get(optional_key)
            if value is not None:
                client[optional_key] = value

        return rest_api_source({"client": client, "resources": resources})
