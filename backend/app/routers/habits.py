"""HTTP routes for habits and check-ins."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import ReadyUser
from app.database import get_db
from app.models import HabitStatus
from app.schemas import (
    CheckInRead,
    HabitCreate,
    HabitRead,
    HabitUpdate,
    WeeklySummaryRead,
)
from app.services import habits as habit_service

router = APIRouter(
    prefix="/habits",
    tags=["habits"],
)
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[HabitRead])
def get_habits(
    db: DatabaseSession,
    user: ReadyUser,
    habit_status: Annotated[HabitStatus | None, Query(alias="status")] = HabitStatus.ACTIVE,
) -> list[HabitRead]:
    """List habits, optionally filtered by status."""
    return [
        HabitRead.model_validate(habit)
        for habit in habit_service.list_habits(
            db,
            user.id,
            habit_status,
        )
    ]


@router.post(
    "",
    response_model=HabitRead,
    status_code=status.HTTP_201_CREATED,
)
def post_habit(
    payload: HabitCreate,
    db: DatabaseSession,
    user: ReadyUser,
) -> HabitRead:
    """Create a habit."""
    return HabitRead.model_validate(
        habit_service.create_habit(
            db,
            user.id,
            payload,
        ),
    )


@router.get(
    "/weekly-summary",
    response_model=WeeklySummaryRead,
)
def get_weekly_summary(
    db: DatabaseSession,
    user: ReadyUser,
    week_start: date | None = None,
    habit_status: Annotated[HabitStatus | None, Query(alias="status")] = HabitStatus.ACTIVE,
) -> WeeklySummaryRead:
    """Return completion totals and current streaks for a week."""
    selected_start = week_start or _current_week_start()
    if selected_start.weekday() != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="week_start must be a Monday",
        )
    return habit_service.build_weekly_summary(
        db,
        user.id,
        selected_start,
        habit_status,
    )


@router.patch(
    "/{habit_id}",
    response_model=HabitRead,
)
def patch_habit(
    habit_id: int,
    payload: HabitUpdate,
    db: DatabaseSession,
    user: ReadyUser,
) -> HabitRead:
    """Partially update a habit."""
    try:
        habit = habit_service.update_habit(
            db,
            user.id,
            habit_id,
            payload,
        )
    except habit_service.HabitNotFoundError as error:
        raise _habit_not_found() from error
    except habit_service.HabitConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Habit direction cannot change after its first check-in",
        ) from error
    return HabitRead.model_validate(habit)


@router.delete(
    "/{habit_id}",
    response_model=HabitRead,
)
def delete_habit(
    habit_id: int,
    db: DatabaseSession,
    user: ReadyUser,
) -> HabitRead:
    """Archive a habit while retaining its check-in history."""
    try:
        habit = habit_service.archive_habit(
            db,
            user.id,
            habit_id,
        )
    except habit_service.HabitNotFoundError as error:
        raise _habit_not_found() from error
    return HabitRead.model_validate(habit)


@router.put(
    "/{habit_id}/check-ins/{check_in_date}",
    response_model=CheckInRead,
)
def put_habit_check_in(
    habit_id: int,
    check_in_date: date,
    db: DatabaseSession,
    user: ReadyUser,
) -> CheckInRead:
    """Idempotently record a habit completion on a date."""
    try:
        check_in, _ = habit_service.put_check_in(
            db,
            user.id,
            habit_id,
            check_in_date,
        )
    except habit_service.HabitNotFoundError as error:
        raise _habit_not_found() from error
    except habit_service.ArchivedHabitError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archived habits cannot receive new check-ins",
        ) from error
    return CheckInRead.model_validate(check_in)


@router.delete(
    "/{habit_id}/check-ins/{check_in_date}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_habit_check_in(
    habit_id: int,
    check_in_date: date,
    db: DatabaseSession,
    user: ReadyUser,
) -> Response:
    """Remove a habit completion from a date."""
    try:
        habit_service.delete_check_in(
            db,
            user.id,
            habit_id,
            check_in_date,
        )
    except habit_service.HabitNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit or check-in not found",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _current_week_start() -> date:
    """Return Monday of the current UTC week."""
    today = datetime.now(UTC).date()
    return today - timedelta(days=today.weekday())


def _habit_not_found() -> HTTPException:
    """Build the standard missing-habit response."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Habit not found",
    )
