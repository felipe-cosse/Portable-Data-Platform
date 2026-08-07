from __future__ import annotations

import pytest

from data_platform.config import ConfigurationError, SourceConfig
from data_platform.connectors import (
    ApiConnector,
    DatabaseConnector,
    FilesystemConnector,
    build_connector,
)


@pytest.mark.parametrize(
    ("connector_type", "expected_type"),
    [
        ("filesystem", FilesystemConnector),
        ("database", DatabaseConnector),
        ("api", ApiConnector),
    ],
)
def test_connector_registry(connector_type: str, expected_type: type) -> None:
    connector = build_connector(SourceConfig(name="example", type=connector_type))

    assert isinstance(connector, expected_type)


def test_connector_registry_rejects_unknown_type() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported connector type"):
        build_connector(SourceConfig(name="example", type="unknown"))
