"""Administrative account provisioning routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import CurrentAdmin, hash_password, revoke_user_sessions
from app.database import get_db
from app.models import User, UserRole, UserStatus
from app.schemas import (
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserUpdate,
    UserRead,
)

router = APIRouter(prefix="/admin/users", tags=["admin"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[UserRead])
def list_users(
    _admin: CurrentAdmin,
    db: DatabaseSession,
) -> list[UserRead]:
    """List account metadata without exposing private domain data."""
    users = db.scalars(select(User).order_by(User.created_at, User.id))
    return [UserRead.model_validate(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    _admin: CurrentAdmin,
    db: DatabaseSession,
) -> UserRead:
    """Provision a user with a temporary password."""
    if db.scalar(select(User.id).where(User.username == payload.username)) is not None:
        raise _username_conflict()
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.temporary_password),
        role=payload.role,
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: CurrentAdmin,
    db: DatabaseSession,
) -> UserRead:
    """Update account metadata while preserving an active administrator."""
    user = db.get(User, user_id)
    if user is None:
        raise _user_not_found()
    resulting_role = payload.role or user.role
    resulting_status = payload.status or user.status
    if user.id == admin.id and resulting_status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes desactivar tu propia cuenta.",
        )
    removes_active_admin = (
        user.role == UserRole.ADMIN
        and user.status == UserStatus.ACTIVE
        and (resulting_role != UserRole.ADMIN or resulting_status != UserStatus.ACTIVE)
    )
    if removes_active_admin and _active_admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Debe permanecer al menos un administrador activo.",
        )
    values = payload.model_dump(exclude_none=True)
    for field, value in values.items():
        setattr(user, field, value)
    user.updated_at = datetime.now(UTC)
    if resulting_status == UserStatus.DISABLED:
        revoke_user_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/{user_id}/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    _admin: CurrentAdmin,
    db: DatabaseSession,
) -> Response:
    """Set a temporary password and revoke every existing session."""
    user = db.get(User, user_id)
    if user is None:
        raise _user_not_found()
    user.password_hash = hash_password(payload.temporary_password)
    user.must_change_password = True
    user.updated_at = datetime.now(UTC)
    revoke_user_sessions(db, user.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _active_admin_count(db: Session) -> int:
    """Return the number of active administrators."""
    return int(
        db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.ADMIN,
                User.status == UserStatus.ACTIVE,
            ),
        )
        or 0,
    )


def _user_not_found() -> HTTPException:
    """Build the standard missing-user response."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Usuario no encontrado.",
    )


def _username_conflict() -> HTTPException:
    """Build the standard duplicate-username response."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Ese nombre de usuario ya existe.",
    )
