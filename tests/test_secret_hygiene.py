from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_metabase_encryption_key_is_not_committed_in_env_template() -> None:
    env_template = (REPOSITORY_ROOT / ".env.example").read_text().splitlines()
    setting = next(
        line
        for line in env_template
        if line.startswith("METABASE_ENCRYPTION_SECRET_KEY=")
    )

    assert setting == "METABASE_ENCRYPTION_SECRET_KEY="


def test_compose_requires_generated_metabase_encryption_key() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text()

    assert "METABASE_ENCRYPTION_SECRET_KEY:?Run make bootstrap" in compose
    assert "METABASE_ENCRYPTION_SECRET_KEY:-" not in compose
