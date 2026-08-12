"""Authentication, administration, and tenant-isolation tests."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import (
    hash_password,
    hash_session_token,
    initialize_bootstrap_admin,
    verify_password,
)
from app.config import Settings
from app.main import app
from app.models import User, UserRole, UserSession, UserStatus

TEST_USERNAME = "admin"
TEST_PASSWORD = "contraseña-segura"
TEMPORARY_PASSWORD = "temporal-segura"
NEW_PASSWORD = "frase-nueva-segura"
EXPECTED_PROVISIONED_USER_COUNT = 2


def test_login_session_logout_and_generic_failure(
    unauthenticated_client: TestClient,
) -> None:
    """Create, resolve, and revoke a session without enumerating accounts."""
    unknown = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "desconocido", "password": "incorrecta"},
    )
    invalid = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": "incorrecta"},
    )
    login = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME.upper(), "password": TEST_PASSWORD},
    )

    assert unknown.status_code == status.HTTP_401_UNAUTHORIZED
    assert invalid.status_code == status.HTTP_401_UNAUTHORIZED
    assert unknown.json()["detail"] == invalid.json()["detail"]
    assert login.status_code == status.HTTP_200_OK
    cookie = login.headers["set-cookie"]
    assert "pleno_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert unauthenticated_client.get("/api/v1/auth/me").json()["username"] == TEST_USERNAME

    logout = unauthenticated_client.post("/api/v1/auth/logout")

    assert logout.status_code == status.HTTP_204_NO_CONTENT
    assert unauthenticated_client.get("/api/v1/auth/me").status_code == status.HTTP_401_UNAUTHORIZED


def test_login_rate_limit_is_local_and_bounded(
    unauthenticated_client: TestClient,
) -> None:
    """Block a sixth recent failure for one username and address."""
    responses = [
        unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "limited-user", "password": "incorrecta"},
        )
        for _ in range(6)
    ]

    assert all(response.status_code == status.HTTP_401_UNAUTHORIZED for response in responses[:5])
    assert responses[5].status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_mandatory_password_change_rotates_sessions_and_unlocks_domain(
    unauthenticated_client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    """Restrict temporary-password sessions until a successful change."""
    with session_factory() as db:
        user = User(
            username="persona",
            display_name="Persona",
            password_hash=hash_password(TEMPORARY_PASSWORD),
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
            must_change_password=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    login = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "persona", "password": TEMPORARY_PASSWORD},
    )
    blocked = unauthenticated_client.get("/api/v1/habits")
    changed = unauthenticated_client.put(
        "/api/v1/auth/password",
        json={
            "current_password": TEMPORARY_PASSWORD,
            "new_password": NEW_PASSWORD,
        },
    )

    assert login.status_code == status.HTTP_200_OK
    assert blocked.status_code == status.HTTP_403_FORBIDDEN
    assert changed.status_code == status.HTTP_200_OK
    assert changed.json()["must_change_password"] is False
    assert unauthenticated_client.get("/api/v1/habits").status_code == status.HTTP_200_OK
    with session_factory() as db:
        session_count = db.scalar(
            select(func.count(UserSession.id)).where(UserSession.user_id == user_id),
        )
        user = db.get(User, user_id)
        assert session_count == 1
        assert user is not None
        assert verify_password(NEW_PASSWORD, user.password_hash)


def test_admin_provisions_updates_resets_and_preserves_last_admin(
    client: TestClient,
) -> None:
    """Manage accounts while preventing self-disable and loss of administration."""
    created = client.post(
        "/api/v1/admin/users",
        json={
            "username": "nuevo.usuario",
            "display_name": "Nueva Persona",
            "temporary_password": TEMPORARY_PASSWORD,
            "role": "member",
        },
    )
    user_id = created.json()["id"]

    duplicate = client.post(
        "/api/v1/admin/users",
        json={
            "username": "NUEVO.USUARIO",
            "display_name": "Otra Persona",
            "temporary_password": TEMPORARY_PASSWORD,
            "role": "member",
        },
    )
    renamed = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"display_name": "Nombre Actualizado", "role": "admin"},
    )
    self_disable = client.patch(
        "/api/v1/admin/users/1",
        json={"status": "disabled"},
    )
    reset = client.post(
        f"/api/v1/admin/users/{user_id}/password-reset",
        json={"temporary_password": NEW_PASSWORD},
    )
    users = client.get("/api/v1/admin/users")

    assert created.status_code == status.HTTP_201_CREATED
    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert renamed.json()["display_name"] == "Nombre Actualizado"
    assert renamed.json()["role"] == "admin"
    assert self_disable.status_code == status.HTTP_409_CONFLICT
    assert reset.status_code == status.HTTP_204_NO_CONTENT
    assert len(users.json()) == EXPECTED_PROVISIONED_USER_COUNT


@pytest.mark.usefixtures("client")
def test_member_cannot_administer_accounts(
    session_factory: sessionmaker[Session],
) -> None:
    """Reject account administration from an authenticated member."""
    token = _create_user_session(session_factory, "miembro", UserRole.MEMBER)

    with TestClient(
        app,
        headers={"Origin": "http://testserver"},
        cookies={"pleno_session": token},
    ) as member_client:
        response = member_client.get("/api/v1/admin/users")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_habits_finance_and_gamification_are_isolated(
    session_factory: sessionmaker[Session],
    client: TestClient,
) -> None:
    """Return 404 for known IDs owned by another account."""
    second_token = _create_user_session(session_factory, "segunda", UserRole.MEMBER)
    first_habit = client.post(
        "/api/v1/habits",
        json={
            "name": "Privado uno",
            "frequency": "daily",
            "color": "#547A67",
        },
    ).json()

    with TestClient(
        app,
        headers={"Origin": "http://testserver"},
        cookies={"pleno_session": second_token},
    ) as second_client:
        second_habit = second_client.post(
            "/api/v1/habits",
            json={
                "name": "Privado dos",
                "frequency": "daily",
                "color": "#A36A4F",
            },
        ).json()
        hidden_habit = second_client.patch(
            f"/api/v1/habits/{first_habit['id']}",
            json={"name": "Intento"},
        )
        settings = second_client.put(
            "/api/v1/finance/settings",
            json={"base_currency": "COP"},
        )
        category = second_client.post(
            "/api/v1/finance/categories",
            json={
                "name": "Comida",
                "type": "expense",
                "color": "#547A67",
            },
        )
        reward = second_client.post(
            "/api/v1/gamification/rewards",
            json={"name": "Descanso", "cost_xp": 10},
        ).json()

    first_list = client.get("/api/v1/habits").json()
    client.put(
        "/api/v1/finance/settings",
        json={"base_currency": "COP"},
    )
    hidden_reward = client.patch(
        f"/api/v1/gamification/rewards/{reward['id']}",
        json={"name": "Intento"},
    )
    hidden_category = client.post(
        "/api/v1/finance/transactions",
        json={
            "type": "expense",
            "amount_minor": 1000,
            "category_id": category.json()["id"],
            "date": "2026-08-09",
            "description": "Intento",
        },
    )

    assert second_habit["id"] != first_habit["id"]
    assert hidden_habit.status_code == status.HTTP_404_NOT_FOUND
    assert settings.status_code in {status.HTTP_200_OK, status.HTTP_201_CREATED}
    assert category.status_code == status.HTTP_201_CREATED
    assert [habit["name"] for habit in first_list] == ["Privado uno"]
    assert hidden_reward.status_code == status.HTTP_404_NOT_FOUND
    assert hidden_category.status_code == status.HTTP_404_NOT_FOUND


def test_authenticated_mutations_require_an_allowed_origin(client: TestClient) -> None:
    """Reject cookie-authenticated writes without a same-origin header."""
    previous_origin = client.headers.pop("origin")
    try:
        response = client.post(
            "/api/v1/habits",
            json={
                "name": "No permitido",
                "frequency": "daily",
                "color": "#547A67",
            },
        )
    finally:
        client.headers["origin"] = previous_origin

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_bootstrap_initializes_once(
    session_factory: sessionmaker[Session],
) -> None:
    """Hash bootstrap credentials once and leave a configured account untouched."""
    with session_factory() as db:
        admin = db.get(User, 1)
        assert admin is not None
        admin.password_hash = "!"
        db.commit()
        settings = Settings(
            bootstrap_admin_username="first.admin",
            bootstrap_admin_display_name="Primera Persona",
            bootstrap_admin_password=TEMPORARY_PASSWORD,
        )
        initialize_bootstrap_admin(db, settings)
        first_hash = admin.password_hash
        initialize_bootstrap_admin(
            db,
            Settings(
                bootstrap_admin_username="different",
                bootstrap_admin_password=NEW_PASSWORD,
            ),
        )
        db.refresh(admin)

    assert admin.username == "first.admin"
    assert admin.display_name == "Primera Persona"
    assert admin.password_hash == first_hash
    assert verify_password(TEMPORARY_PASSWORD, first_hash)


def _create_user_session(
    session_factory: sessionmaker[Session],
    username: str,
    role: UserRole,
) -> str:
    """Create a ready account and return its raw browser token."""
    token = f"session-{username}"
    with session_factory() as db:
        user = User(
            username=username,
            display_name=username.title(),
            password_hash=hash_password(TEMPORARY_PASSWORD),
            role=role,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.add(user)
        db.flush()
        db.add(
            UserSession(
                token_hash=hash_session_token(token),
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        )
        db.commit()
    return token
