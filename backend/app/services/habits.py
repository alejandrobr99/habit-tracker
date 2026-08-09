"""Business logic for habits and check-ins."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Habit, HabitCheckIn, HabitFrequency, HabitStatus
from app.schemas import (
    HabitCreate,
    HabitUpdate,
    HabitWeeklySummary,
    WeeklySummaryRead,
)


class HabitNotFoundError(Exception):
    """Raised when a requested habit does not exist."""


class ArchivedHabitError(Exception):
    """Raised when a new check-in is requested for an archived habit."""


def list_habits(
    db: Session,
    status: HabitStatus | None,
) -> list[Habit]:
    """Return habits, optionally filtered by lifecycle status."""
    statement = select(Habit).order_by(Habit.created_at, Habit.id)
    if status is not None:
        statement = statement.where(Habit.status == status)
    return list(db.scalars(statement))


def get_habit(
    db: Session,
    habit_id: int,
) -> Habit:
    """Return a habit or raise when it does not exist."""
    habit = db.get(Habit, habit_id)
    if habit is None:
        raise HabitNotFoundError
    return habit


def create_habit(
    db: Session,
    payload: HabitCreate,
) -> Habit:
    """Create and persist a habit."""
    habit = Habit(**payload.model_dump())
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


def update_habit(
    db: Session,
    habit_id: int,
    payload: HabitUpdate,
) -> Habit:
    """Apply a partial update to an existing habit."""
    habit = get_habit(db, habit_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    habit.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(habit)
    return habit


def archive_habit(
    db: Session,
    habit_id: int,
) -> Habit:
    """Archive a habit without removing its history."""
    habit = get_habit(db, habit_id)
    habit.status = HabitStatus.ARCHIVED
    habit.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(habit)
    return habit


def put_check_in(
    db: Session,
    habit_id: int,
    check_in_date: date,
) -> tuple[HabitCheckIn, bool]:
    """Create a check-in or return the existing check-in for the date."""
    habit = get_habit(db, habit_id)
    if habit.status == HabitStatus.ARCHIVED:
        raise ArchivedHabitError
    statement = select(HabitCheckIn).where(
        HabitCheckIn.habit_id == habit_id,
        HabitCheckIn.check_in_date == check_in_date,
    )
    existing = db.scalar(statement)
    if existing is not None:
        return existing, False
    check_in = HabitCheckIn(
        habit_id=habit_id,
        check_in_date=check_in_date,
    )
    db.add(check_in)
    db.commit()
    db.refresh(check_in)
    return check_in, True


def delete_check_in(
    db: Session,
    habit_id: int,
    check_in_date: date,
) -> None:
    """Delete a habit check-in for a date."""
    get_habit(db, habit_id)
    statement = select(HabitCheckIn).where(
        HabitCheckIn.habit_id == habit_id,
        HabitCheckIn.check_in_date == check_in_date,
    )
    check_in = db.scalar(statement)
    if check_in is None:
        raise HabitNotFoundError
    db.delete(check_in)
    db.commit()


def calculate_streak(
    check_in_dates: set[date],
    frequency: HabitFrequency,
    as_of: date,
) -> int:
    """Calculate the current daily or weekly completion streak."""
    if not check_in_dates:
        return 0
    if frequency == HabitFrequency.DAILY:
        return _calculate_daily_streak(check_in_dates, as_of)
    return _calculate_weekly_streak(check_in_dates, as_of)


def _calculate_daily_streak(
    check_in_dates: set[date],
    as_of: date,
) -> int:
    """Calculate a daily streak, allowing the current day to be incomplete."""
    cursor = as_of
    if cursor not in check_in_dates:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in check_in_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _calculate_weekly_streak(
    check_in_dates: set[date],
    as_of: date,
) -> int:
    """Calculate a weekly streak, allowing the current week to be incomplete."""
    completed_weeks = {
        check_in_date - timedelta(days=check_in_date.weekday()) for check_in_date in check_in_dates
    }
    cursor = as_of - timedelta(days=as_of.weekday())
    if cursor not in completed_weeks:
        cursor -= timedelta(weeks=1)
    streak = 0
    while cursor in completed_weeks:
        streak += 1
        cursor -= timedelta(weeks=1)
    return streak


def build_weekly_summary(
    db: Session,
    week_start: date,
    status: HabitStatus | None,
) -> WeeklySummaryRead:
    """Build habit completion and streak data for a Monday-based week."""
    week_end = week_start + timedelta(days=6)
    habits = list_habits(db, status)
    summaries = [
        _build_habit_summary(
            db,
            habit,
            week_start,
            week_end,
        )
        for habit in habits
    ]
    return WeeklySummaryRead(
        week_start=week_start,
        week_end=week_end,
        habits=summaries,
    )


def _build_habit_summary(
    db: Session,
    habit: Habit,
    week_start: date,
    week_end: date,
) -> HabitWeeklySummary:
    """Build one habit's weekly summary."""
    statement = (
        select(HabitCheckIn.check_in_date)
        .where(
            HabitCheckIn.habit_id == habit.id,
            HabitCheckIn.check_in_date <= week_end,
        )
        .order_by(HabitCheckIn.check_in_date)
    )
    all_dates = set(db.scalars(statement))
    weekly_dates = sorted(
        check_in_date for check_in_date in all_dates if week_start <= check_in_date <= week_end
    )
    as_of = min(datetime.now(UTC).date(), week_end)
    return HabitWeeklySummary(
        habit=habit,
        check_in_dates=weekly_dates,
        completed_count=len(weekly_dates),
        target_count=7 if habit.frequency == HabitFrequency.DAILY else 1,
        current_streak=calculate_streak(
            all_dates,
            habit.frequency,
            as_of,
        ),
    )
