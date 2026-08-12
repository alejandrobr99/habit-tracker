"""Security control tests: origin derivation, budgets, body size, and passwords."""

import logging
from collections.abc import Generator, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

from app.config import Settings
from app.database import get_db
from app.main import create_app
from app.security import (
    MAX_LOGIN_FAILURES_PER_ORIGIN,
    AttemptLimiter,
    log_security_event,
    password_policy_error,
    resolve_client_ip,
    security_logger,
)

TEST_PASSWORD = "contraseña-segura"
STRONG_PASSWORD = "frase-nueva-segura"
PROXY_HOPS = 1
LEDGER_CAPACITY = 8
PROBED_KEYS = 50


@pytest.fixture
def proxied_client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    """Provide a client for an app that trusts exactly one proxy."""
    application = create_app(Settings(trusted_proxy_hops=PROXY_HOPS))

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(
        application,
        headers={"Origin": "http://testserver"},
    ) as test_client:
        yield test_client
    application.dependency_overrides.clear()


def build_request(forwarded_for: str | None, peer: str | None = "10.0.0.9") -> Request:
    """Build a minimal request carrying the given proxy header and peer."""
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for is not None else []
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (peer, 4242) if peer else None,
        },
    )


def test_client_ip_ignores_forwarded_header_without_declared_proxies():
    settings = Settings(trusted_proxy_hops=0)

    resolved = resolve_client_ip(build_request("203.0.113.7"), settings)

    assert resolved == "10.0.0.9"


def test_client_ip_uses_the_entry_added_by_the_declared_proxy():
    settings = Settings(trusted_proxy_hops=1)

    spoofed = resolve_client_ip(build_request("203.0.113.7, 198.51.100.4"), settings)
    single = resolve_client_ip(build_request("198.51.100.4"), settings)
    missing = resolve_client_ip(build_request(None), settings)

    assert spoofed == "198.51.100.4"
    assert single == "198.51.100.4"
    assert missing == "10.0.0.9"


def test_client_ip_falls_back_when_no_peer_is_available():
    settings = Settings(trusted_proxy_hops=0)

    resolved = resolve_client_ip(build_request(None, peer=None), settings)

    assert resolved == "unknown"


def test_login_budget_survives_a_rotating_forwarded_address(
    proxied_client: TestClient,
) -> None:
    """Keep blocking one account even when every attempt claims a new address."""
    responses = [
        proxied_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "incorrecta"},
            headers={"X-Forwarded-For": f"198.51.100.{index}"},
        )
        for index in range(6)
    ]

    assert all(response.status_code == status.HTTP_401_UNAUTHORIZED for response in responses[:5])
    assert responses[5].status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_origin_budget_blocks_spraying_across_accounts(
    proxied_client: TestClient,
) -> None:
    """Block one address that keeps failing against many different accounts."""
    attempts = MAX_LOGIN_FAILURES_PER_ORIGIN + 1
    responses = [
        proxied_client.post(
            "/api/v1/auth/login",
            json={"username": f"cuenta{index}", "password": "incorrecta"},
            headers={"X-Forwarded-For": "198.51.100.30"},
        )
        for index in range(attempts)
    ]

    assert responses[MAX_LOGIN_FAILURES_PER_ORIGIN - 1].status_code == (
        status.HTTP_401_UNAUTHORIZED
    )
    assert responses[MAX_LOGIN_FAILURES_PER_ORIGIN].status_code == (
        status.HTTP_429_TOO_MANY_REQUESTS
    )


def test_a_successful_login_releases_the_budget(proxied_client: TestClient) -> None:
    """Clear recorded failures once the correct credentials arrive."""
    address = {"X-Forwarded-For": "198.51.100.44"}
    for _ in range(4):
        proxied_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "incorrecta"},
            headers=address,
        )

    accepted = proxied_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": TEST_PASSWORD},
        headers=address,
    )
    retried = proxied_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "incorrecta"},
        headers=address,
    )

    assert accepted.status_code == status.HTTP_200_OK
    assert retried.status_code == status.HTTP_401_UNAUTHORIZED


def test_probing_a_budget_never_allocates_an_entry():
    limiter = AttemptLimiter(max_failures=5, max_keys=LEDGER_CAPACITY)
    now = datetime.now(UTC)

    blocked = [limiter.is_blocked(f"key-{index}", now) for index in range(PROBED_KEYS)]

    assert not any(blocked)
    assert limiter.tracked_keys == 0


def test_ledger_stays_within_capacity_under_many_keys():
    limiter = AttemptLimiter(max_failures=5, max_keys=LEDGER_CAPACITY)
    now = datetime.now(UTC)

    for index in range(PROBED_KEYS):
        limiter.record_failure(f"key-{index}", now)

    assert limiter.tracked_keys <= LEDGER_CAPACITY


def test_ledger_drops_keys_whose_window_expired():
    limiter = AttemptLimiter(max_failures=5, window=timedelta(minutes=15))
    now = datetime.now(UTC)
    limiter.record_failure("stale", now - timedelta(minutes=30))

    assert limiter.is_blocked("stale", now) is False


def test_repeated_failures_do_not_grow_a_single_entry():
    limiter = AttemptLimiter(max_failures=3)
    now = datetime.now(UTC)

    for _ in range(100):
        limiter.record_failure("same", now)

    assert limiter.is_blocked("same", now) is True
    assert limiter.tracked_keys == 1


def test_oversized_declared_body_is_rejected(client: TestClient) -> None:
    """Refuse a body whose declared length exceeds the maximum."""
    response = client.post(
        "/api/v1/habits",
        content=b"x" * 70_000,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json()["detail"]


def test_oversized_streamed_body_is_rejected(client: TestClient) -> None:
    """Refuse a body that omits its length and then exceeds the maximum."""

    def chunks() -> Iterator[bytes]:
        for _ in range(20):
            yield b"x" * 8_192

    response = client.post(
        "/api/v1/habits",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE


def test_body_within_the_maximum_is_accepted(client: TestClient) -> None:
    """Keep accepting a normal payload."""
    response = client.post(
        "/api/v1/habits",
        json={
            "name": "Caminar",
            "description": "d" * 2_000,
            "frequency": "daily",
            "color": "#547A67",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "password",
    [
        "administrador",
        "aaaaaaaaaaaaaa",
        "121212121212",
        "admin-admin-admin",
    ],
)
def test_password_policy_rejects_trivial_values(password: str) -> None:
    """Reject repetition, common values, and passwords built from the username."""
    assert password_policy_error(password, "admin") is not None


def test_password_policy_accepts_a_personal_phrase():
    assert password_policy_error(STRONG_PASSWORD, "admin") is None


def test_password_change_rejects_a_password_holding_the_username(
    client: TestClient,
) -> None:
    """Answer 422 when the new password contains the account username."""
    response = client.put(
        "/api/v1/auth/password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "admin-y-mas-texto",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_password_change_is_rate_limited(client: TestClient) -> None:
    """Stop unlimited guessing of the current password from a valid session."""
    responses = [
        client.put(
            "/api/v1/auth/password",
            json={
                "current_password": "incorrecta",
                "new_password": STRONG_PASSWORD,
            },
        )
        for _ in range(6)
    ]

    assert all(response.status_code == status.HTTP_400_BAD_REQUEST for response in responses[:5])
    assert responses[5].status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_admin_provisioning_rejects_a_trivial_temporary_password(
    client: TestClient,
) -> None:
    """Refuse a provisioned or reset password that is trivially guessable."""
    created = client.post(
        "/api/v1/admin/users",
        json={
            "username": "nueva.persona",
            "display_name": "Nueva Persona",
            "temporary_password": "nueva.persona-1",
            "role": "member",
        },
    )
    reset = client.post(
        "/api/v1/admin/users/1/password-reset",
        json={"temporary_password": "aaaaaaaaaaaaaa"},
    )

    assert created.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert reset.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_identity_payloads_reject_undeclared_fields(
    unauthenticated_client: TestClient,
) -> None:
    """Refuse a login body carrying a field the contract does not declare."""
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": TEST_PASSWORD, "role": "admin"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_security_events_cannot_forge_extra_log_lines() -> None:
    """Collapse hostile characters so one event stays on one line."""
    recorded: list[str] = []

    class Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            recorded.append(record.getMessage())

    collector = Collector()
    security_logger.addHandler(collector)
    try:
        log_security_event(
            "login_failed",
            username="victima\nevent=login_succeeded user_id=1",
        )
    finally:
        security_logger.removeHandler(collector)

    assert len(recorded) == 1
    assert "\n" not in recorded[0]
    assert "event=login_succeeded" not in recorded[0]


def test_security_events_omit_absent_fields() -> None:
    """Leave a field out of the line instead of writing an empty value."""
    recorded: list[str] = []

    class Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            recorded.append(record.getMessage())

    collector = Collector()
    security_logger.addHandler(collector)
    try:
        log_security_event("login_succeeded", user_id=7, client_ip=None)
    finally:
        security_logger.removeHandler(collector)

    assert "user_id=7" in recorded[0]
    assert "client_ip" not in recorded[0]
