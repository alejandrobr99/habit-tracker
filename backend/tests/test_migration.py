"""Alembic verification for empty and populated pre-authentication databases."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.config import get_settings


def test_multi_user_migration_preserves_existing_ids_and_assigns_owner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Assign historical aggregates to the initial administrator without loss."""
    database_path = tmp_path / "migrated.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("PLANNER_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "20260808_0003")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO habits "
                "(id, name, description, direction, frequency, status, color, "
                "created_at, updated_at) "
                "VALUES (42, 'Histórico', NULL, 'build', 'daily', 'active', "
                "'#547A67', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ),
        )
        connection.execute(
            text(
                "INSERT INTO finance_settings "
                "(id, base_currency, minor_unit, created_at, updated_at) "
                "VALUES (1, 'COP', 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ),
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        habit = connection.execute(
            text("SELECT id, user_id FROM habits"),
        ).one()
        settings = connection.execute(
            text("SELECT id, user_id FROM finance_settings"),
        ).one()
        admin = connection.execute(
            text("SELECT id, password_hash FROM users"),
        ).one()

    assert habit == (42, 1)
    assert settings == (1, 1)
    assert admin == (1, "!")
    engine.dispose()
    get_settings.cache_clear()


def test_multi_user_migration_builds_empty_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Build the final authentication schema from an empty database."""
    database_path = tmp_path / "clean.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("PLANNER_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'"),
            )
        }
        owner = connection.execute(
            text("SELECT user_id FROM finance_settings"),
        ).first()

    assert {"users", "user_sessions", "habits", "finance_settings"} <= tables
    assert owner is None
    engine.dispose()
    get_settings.cache_clear()
