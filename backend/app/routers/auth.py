"""Session authentication routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import (
    AppSettings,
    CurrentUser,
    authenticate_user,
    clear_session_cookie,
    create_session,
    hash_password,
    login_attempt_limiter,
    revoke_session_token,
    revoke_user_sessions,
    set_session_cookie,
    verify_password,
)
from app.database import get_db
from app.schemas import LoginRequest, PasswordChangeRequest, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DatabaseSession,
    settings: AppSettings,
) -> UserRead:
    """Validate credentials and create a revocable session."""
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(UTC)
    if login_attempt_limiter.is_blocked(payload.username, client_ip, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
        )
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        login_attempt_limiter.record_failure(payload.username, client_ip, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )
    login_attempt_limiter.clear(payload.username, client_ip)
    created_session = create_session(db, user)
    set_session_cookie(response, created_session, settings)
    return UserRead.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: DatabaseSession,
    settings: AppSettings,
) -> None:
    """Revoke the current session when present and clear its cookie."""
    token = request.cookies.get("pleno_session")
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
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La contraseña nueva debe ser diferente.",
        )
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    revoke_user_sessions(db, user.id)
    db.flush()
    created_session = create_session(db, user)
    set_session_cookie(response, created_session, settings)
    db.refresh(user)
    return UserRead.model_validate(user)
