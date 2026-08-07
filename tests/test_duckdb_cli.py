from __future__ import annotations

from pathlib import Path

from data_platform.duckdb_cli import query_file


def test_query_file_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "values.csv"
    path.write_text("id,value\n1,10\n2,15\n", encoding="utf-8")

    result = query_file(str(path), "select sum(value) from source")

    assert result == [(25,)]
