from __future__ import annotations

from pathlib import Path

import pytest

from data_platform.config import (
    ConfigurationError,
    default_source_config_path,
    load_source_configs,
)


def _write_config(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_disabled_source_does_not_require_secret(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path / "sources.yml",
        """
version: 1
sources:
  - name: optional_api
    type: api
    enabled: false
    base_url: https://example.com/
    auth:
      token: ${TOKEN_THAT_DOES_NOT_EXIST}
""",
    )

    [source] = load_source_configs(path)

    assert source.enabled is False
    assert source.options["auth"]["token"] == "${TOKEN_THAT_DOES_NOT_EXIST}"


def test_enabled_source_expands_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_BUCKET", "example-bucket")
    path = _write_config(
        tmp_path / "sources.yml",
        """
version: 1
sources:
  - name: files
    type: filesystem
    bucket_url: s3://${TEST_BUCKET}/landing
""",
    )

    [source] = load_source_configs(path)

    assert source.options["bucket_url"] == "s3://example-bucket/landing"
    assert source.dataset_name == "raw_files"


def test_enabled_source_reports_missing_environment(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path / "sources.yml",
        """
version: 1
sources:
  - name: files
    type: filesystem
    bucket_url: s3://${MISSING_TEST_BUCKET}/landing
""",
    )

    with pytest.raises(ConfigurationError, match="MISSING_TEST_BUCKET"):
        load_source_configs(path)


def test_duplicate_source_names_are_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path / "sources.yml",
        """
version: 1
sources:
  - name: duplicate
    type: api
  - name: duplicate
    type: filesystem
""",
    )

    with pytest.raises(ConfigurationError, match="Duplicate source name"):
        load_source_configs(path)


def test_default_source_config_uses_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = _write_config(tmp_path / "config" / "sources.yml", "version: 1\nsources: []\n")
    monkeypatch.delenv("SOURCE_CONFIG_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    assert default_source_config_path() == expected
