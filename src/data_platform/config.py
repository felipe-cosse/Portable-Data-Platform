from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class ConfigurationError(ValueError):
    """Raised when connector configuration is invalid."""


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    enabled: bool = True
    dataset: str | None = None
    write_disposition: str = "append"
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def dataset_name(self) -> str:
        return self.dataset or f"raw_{self.name}"


def _expand_environment(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_environment(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_environment(item) for item in value]
    if not isinstance(value, str):
        return value

    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        variable = match.group(1)
        if variable not in os.environ:
            missing.add(variable)
            return match.group(0)
        return os.environ[variable]

    expanded = _ENV_PATTERN.sub(replace, value)
    if missing:
        names = ", ".join(sorted(missing))
        raise ConfigurationError(f"Missing environment variable(s): {names}")
    return expanded


def load_source_configs(path: str | Path) -> list[SourceConfig]:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigurationError(f"Source configuration does not exist: {config_path}")

    with config_path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream) or {}

    if document.get("version") != 1:
        raise ConfigurationError("Source configuration must declare version: 1")

    raw_sources = document.get("sources")
    if not isinstance(raw_sources, list):
        raise ConfigurationError("Source configuration must contain a sources list")

    configs: list[SourceConfig] = []
    seen: set[str] = set()
    for index, raw_source in enumerate(raw_sources):
        if not isinstance(raw_source, dict):
            raise ConfigurationError(f"sources[{index}] must be a mapping")

        name = raw_source.get("name")
        source_type = raw_source.get("type")
        if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
            raise ConfigurationError(
                f"sources[{index}].name must match {_NAME_PATTERN.pattern!r}"
            )
        if name in seen:
            raise ConfigurationError(f"Duplicate source name: {name}")
        seen.add(name)
        if not isinstance(source_type, str) or not source_type:
            raise ConfigurationError(f"sources[{index}].type is required")

        enabled = raw_source.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ConfigurationError(f"sources[{index}].enabled must be true or false")

        write_disposition = raw_source.get("write_disposition", "append")
        if write_disposition not in {"append", "replace", "merge"}:
            raise ConfigurationError(
                f"{name}.write_disposition must be append, replace, or merge"
            )

        reserved = {
            "name",
            "type",
            "enabled",
            "dataset",
            "write_disposition",
        }
        options = {key: value for key, value in raw_source.items() if key not in reserved}
        if enabled:
            options = _expand_environment(options)

        configs.append(
            SourceConfig(
                name=name,
                type=source_type,
                enabled=enabled,
                dataset=raw_source.get("dataset"),
                write_disposition=write_disposition,
                options=options,
            )
        )

    return configs


def default_source_config_path() -> Path:
    configured = os.getenv("SOURCE_CONFIG_PATH")
    if configured:
        return Path(configured)

    working_directory_config = Path.cwd() / "config" / "sources.yml"
    if working_directory_config.is_file():
        return working_directory_config

    return Path(__file__).resolve().parents[2] / "config" / "sources.yml"
