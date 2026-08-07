from pathlib import Path

from data_platform.metabase_provision import (
    dashboard_card_specs,
    load_env_file,
    native_dataset_query,
)


def test_load_env_file_preserves_process_values(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\nMETABASE_ADMIN_EMAIL=admin@example.com\nQUOTED='value with spaces'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("METABASE_ADMIN_EMAIL", "existing@example.com")

    load_env_file(env_file)

    assert __import__("os").environ["METABASE_ADMIN_EMAIL"] == "existing@example.com"
    assert __import__("os").environ["QUOTED"] == "value with spaces"


def test_dashboard_specs_cover_summary_diagnosis_and_detail() -> None:
    specs = dashboard_card_specs("analytics")

    assert len(specs) == 7
    assert [spec.display for spec in specs[:4]] == ["scalar"] * 4
    assert [spec.display for spec in specs[4:]] == ["bar", "bar", "table"]
    assert all("`analytics`.`customer_activity`" in spec.sql for spec in specs)
    assert all("{{segment}}" in spec.sql for spec in specs)
    assert specs[-1].size_x == 24


def test_native_query_uses_clickhouse_and_segment_template_tag() -> None:
    query = native_dataset_query(42, "SELECT 1")

    assert query["database"] == 42
    assert query["type"] == "native"
    assert query["native"]["query"] == "SELECT 1"
    assert query["native"]["template-tags"]["segment"]["type"] == "text"
