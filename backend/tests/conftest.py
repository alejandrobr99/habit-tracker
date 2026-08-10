"""Shared API test fixtures."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password, hash_session_token
from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole, UserSession, UserStatus

TEST_USERNAME = "admin"
TEST_PASSWORD = "contraseña-segura"
TEST_SESSION_TOKEN = "test-session-token"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


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
    with testing_session() as session:
        session.add(
            User(
                id=1,
                username=TEST_USERNAME,
                display_name="Administrador",
                password_hash=TEST_PASSWORD_HASH,
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                must_change_password=False,
            ),
        )
        session.add(
            UserSession(
                token_hash=hash_session_token(TEST_SESSION_TOKEN),
                user_id=1,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )
        session.commit()
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
    with TestClient(
        app,
        headers={"Origin": "http://testserver"},
        cookies={"pleno_session": TEST_SESSION_TOKEN},
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """Provide an API client without a browser session."""

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(
        app,
        headers={"Origin": "http://testserver"},
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
