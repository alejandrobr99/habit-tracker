"""Password, session, bootstrap, and authorization helpers."""

from __future__ import annotations

import hashlib
import re
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import User, UserRole, UserSession, UserStatus

SESSION_COOKIE_NAME = "pleno_session"
SESSION_LIFETIME = timedelta(days=14)
LOGIN_WINDOW = timedelta(minutes=15)
MAX_LOGIN_FAILURES = 5
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MAX_DISPLAY_NAME_LENGTH = 80
USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,40}$")
PASSWORD_HASH = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = PASSWORD_HASH.hash("contraseña-ficticia-no-utilizable")
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True)
class CreatedSession:
    """A session token and its persisted metadata."""

    token: str
    expires_at: datetime


class LoginAttemptLimiter:
    """Small in-process limiter suitable for the single deployed replica."""

    def __init__(self) -> None:
        """Create an empty failure ledger."""
        self._failures: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)

    def is_blocked(self, username: str, client_ip: str, now: datetime) -> bool:
        """Return whether recent failures reached the configured limit."""
        failures = self._recent_failures(username, client_ip, now)
        return len(failures) >= MAX_LOGIN_FAILURES

    def record_failure(self, username: str, client_ip: str, now: datetime) -> None:
        """Record one failed login."""
        failures = self._recent_failures(username, client_ip, now)
        failures.append(now)

    def clear(self, username: str, client_ip: str) -> None:
        """Clear failures after a successful login."""
        self._failures.pop((username, client_ip), None)

    def _recent_failures(
        self,
        username: str,
        client_ip: str,
        now: datetime,
    ) -> deque[datetime]:
        failures = self._failures[(username, client_ip)]
        cutoff = now - LOGIN_WINDOW
        while failures and failures[0] <= cutoff:
            failures.popleft()
        return failures


login_attempt_limiter = LoginAttemptLimiter()


def hash_password(password: str) -> str:
    """Hash a password with the configured Argon2id profile."""
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing malformed bootstrap hashes."""
    candidate_hash = password_hash if password_hash != "!" else DUMMY_PASSWORD_HASH
    try:
        return PASSWORD_HASH.verify(password, candidate_hash)
    except Exception:  # pragma: no cover - defensive compatibility with persisted hashes
        return False


def initialize_bootstrap_admin(db: Session, settings: Settings) -> None:
    """Initialize the migrated administrator exactly once."""
    user = db.get(User, 1)
    if user is None:
        msg = "The initial administrator row is missing. Run database migrations."
        raise RuntimeError(msg)
    if user.password_hash != "!":
        return
    username = (
        (
            settings.bootstrap_admin_username
            or ("admin" if settings.environment == "development" else "")
        )
        .strip()
        .lower()
    )
    password = (
        settings.bootstrap_admin_password.get_secret_value()
        if settings.bootstrap_admin_password is not None
        else ("pleno-local-2026" if settings.environment == "development" else "")
    )
    display_name = settings.bootstrap_admin_display_name.strip()
    if not USERNAME_PATTERN.fullmatch(username) or not (
        MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH
    ):
        msg = (
            "Initialize the first administrator with valid "
            "PLANNER_BOOTSTRAP_ADMIN_USERNAME and PLANNER_BOOTSTRAP_ADMIN_PASSWORD."
        )
        raise RuntimeError(msg)
    if not display_name or len(display_name) > MAX_DISPLAY_NAME_LENGTH:
        msg = "PLANNER_BOOTSTRAP_ADMIN_DISPLAY_NAME must contain 1 to 80 characters."
        raise RuntimeError(msg)
    conflict = db.scalar(select(User.id).where(User.username == username, User.id != user.id))
    if conflict is not None:
        msg = "The bootstrap administrator username is already in use."
        raise RuntimeError(msg)
    user.username = username
    user.display_name = display_name
    user.password_hash = hash_password(password)
    user.role = UserRole.ADMIN
    user.status = UserStatus.ACTIVE
    user.must_change_password = True
    user.updated_at = datetime.now(UTC)
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Return an active account when credentials are valid."""
    user = db.scalar(select(User).where(User.username == username))
    candidate_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    valid = verify_password(password, candidate_hash)
    if user is None or not valid or user.status != UserStatus.ACTIVE:
        return None
    return user


def create_session(db: Session, user: User) -> CreatedSession:
    """Create and persist a new opaque session."""
    now = datetime.now(UTC)
    delete_expired_sessions(db, now)
    token = secrets.token_urlsafe(32)
    expires_at = now + SESSION_LIFETIME
    db.add(
        UserSession(
            token_hash=hash_session_token(token),
            user_id=user.id,
            created_at=now,
            expires_at=expires_at,
        ),
    )
    db.commit()
    return CreatedSession(token=token, expires_at=expires_at)


def delete_expired_sessions(db: Session, now: datetime | None = None) -> None:
    """Delete all sessions whose lifetime ended."""
    db.execute(
        delete(UserSession).where(
            UserSession.expires_at <= (now or datetime.now(UTC)),
        ),
    )


def revoke_user_sessions(db: Session, user_id: int) -> None:
    """Delete every session owned by a user."""
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))


def revoke_session_token(db: Session, token: str) -> None:
    """Delete a session identified by its browser token."""
    db.execute(
        delete(UserSession).where(
            UserSession.token_hash == hash_session_token(token),
        ),
    )
    db.commit()


def hash_session_token(token: str) -> str:
    """Return the stable SHA-256 digest used for token lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


def set_session_cookie(
    response: Response,
    created_session: CreatedSession,
    settings: Settings,
) -> None:
    """Attach a secure session cookie to a response."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=created_session.token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        expires=created_session.expires_at,
        path="/",
        secure=settings.environment == "production",
        httponly=True,
        samesite="strict",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    """Expire the browser session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.environment == "production",
        httponly=True,
        samesite="strict",
    )


def get_current_user(request: Request, db: DatabaseSession) -> User:
    """Resolve the active account represented by the session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise _unauthorized()
    now = datetime.now(UTC)
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_session_token(token)),
    ).one_or_none()
    if row is None:
        raise _unauthorized()
    session, user = row
    if session.expires_at <= now:
        db.delete(session)
        db.commit()
        raise _unauthorized()
    if user.status != UserStatus.ACTIVE:
        revoke_user_sessions(db, user.id)
        db.commit()
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_ready_user(user: CurrentUser) -> User:
    """Require a session whose initial password was already changed."""
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes cambiar tu contraseña antes de continuar.",
        )
    return user


ReadyUser = Annotated[User, Depends(require_ready_user)]


def require_admin(user: ReadyUser, db: DatabaseSession) -> User:
    """Require an administrator while ensuring one remains active."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere una cuenta administradora.",
        )
    active_admins = db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.ADMIN,
            User.status == UserStatus.ACTIVE,
        ),
    )
    if not active_admins:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No existe un administrador activo.",
        )
    return user


CurrentAdmin = Annotated[User, Depends(require_admin)]


def _unauthorized() -> HTTPException:
    """Build the standard session failure response."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión requerida.",
    )
