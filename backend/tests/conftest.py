"""Shared API test fixtures."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def session_factory(
    tmp_path: Path,
) -> Generator[sessionmaker[Session], None, None]:
    """Provide sessions backed by a temporary SQLite database."""
    database_path = tmp_path / "planner-test.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(engine)
    yield testing_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """Provide an API client backed by the temporary database."""

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
