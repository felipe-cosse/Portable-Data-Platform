from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_platform.config import ConfigurationError
from data_platform.connectors.filesystem import _iter_json_records


def test_iter_json_records_reads_array(tmp_path: Path) -> None:
    path = tmp_path / "events.json"
    path.write_text(json.dumps([{"id": 1}, {"id": 2}]), encoding="utf-8")

    records = list(_iter_json_records(str(path), {}, None))

    assert records == [{"id": 1}, {"id": 2}]


def test_iter_json_records_supports_nested_records_path(tmp_path: Path) -> None:
    path = tmp_path / "response.json"
    path.write_text(json.dumps({"data": {"items": [{"id": 3}]}}), encoding="utf-8")

    records = list(_iter_json_records(str(path), {}, "data.items"))

    assert records == [{"id": 3}]


def test_iter_json_records_rejects_scalar_arrays(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([1, 2]), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="arrays must contain objects"):
        list(_iter_json_records(str(path), {}, None))
