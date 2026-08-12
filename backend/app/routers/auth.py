"""Session authentication routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE_NAME,
    AppSettings,
    CurrentUser,
    authenticate_user,
    clear_session_cookie,
    create_session,
    hash_password,
    require_acceptable_password,
    revoke_session_token,
    revoke_user_sessions,
    set_session_cookie,
    verify_password,
)
from app.database import get_db
from app.schemas import LoginRequest, PasswordChangeRequest, UserRead
from app.security import (
    log_security_event,
    login_account_limiter,
    login_origin_limiter,
    password_change_limiter,
    resolve_client_ip,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DatabaseSession = Annotated[Session, Depends(get_db)]
TOO_MANY_ATTEMPTS_DETAIL = "Demasiados intentos. Espera unos minutos e inténtalo de nuevo."


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DatabaseSession,
    settings: AppSettings,
) -> UserRead:
    """Validate credentials and create a revocable session."""
    client_ip = resolve_client_ip(request, settings)
    now = datetime.now(UTC)
    if login_account_limiter.is_blocked(payload.username, now) or login_origin_limiter.is_blocked(
        client_ip,
        now,
    ):
        log_security_event(
            "login_rate_limited",
            username=payload.username,
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=TOO_MANY_ATTEMPTS_DETAIL,
        )
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        login_account_limiter.record_failure(payload.username, now)
        login_origin_limiter.record_failure(client_ip, now)
        log_security_event(
            "login_failed",
            username=payload.username,
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )
    login_account_limiter.clear(payload.username)
    login_origin_limiter.clear(client_ip)
    created_session = create_session(db, user)
    set_session_cookie(response, created_session, settings)
    log_security_event("login_succeeded", user_id=user.id, client_ip=client_ip)
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: DatabaseSession,
    settings: AppSettings,
) -> None:
    """Revoke the current session when present and clear its cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        revoke_session_token(db, token)
    clear_session_cookie(response, settings)


@router.get("/me", response_model=UserRead)
def get_me(user: CurrentUser) -> UserRead:
    """Return the account represented by the current session."""
    return UserRead.model_validate(user)


@router.put("/password", response_model=UserRead)
def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    user: CurrentUser,
    db: DatabaseSession,
    settings: AppSettings,
) -> UserRead:
    """Change the current password and rotate every active session."""
    account_key = str(user.id)
    now = datetime.now(UTC)
    if password_change_limiter.is_blocked(account_key, now):
        log_security_event("password_change_rate_limited", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=TOO_MANY_ATTEMPTS_DETAIL,
        )
    if not verify_password(payload.current_password, user.password_hash):
        password_change_limiter.record_failure(account_key, now)
        log_security_event("password_change_failed", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La contraseña nueva debe ser diferente.",
        )
    require_acceptable_password(payload.new_password, user.username)
    password_change_limiter.clear(account_key)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    revoke_user_sessions(db, user.id)
    db.flush()
    created_session = create_session(db, user)
    set_session_cookie(response, created_session, settings)
    db.refresh(user)
    log_security_event("password_changed", user_id=user.id)
    return UserRead.model_validate(user)
