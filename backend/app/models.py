"""SQLAlchemy domain models."""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC datetimes and restore timezone information on SQLite."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        _dialect: Dialect,
    ) -> datetime | None:
        """Normalize bound datetimes to naive UTC for portable persistence."""
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires a timezone-aware value")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(
        self,
        value: datetime | None,
        _dialect: Dialect,
    ) -> datetime | None:
        """Restore persisted datetimes as timezone-aware UTC values."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class HabitFrequency(StrEnum):
    """Supported habit recurrence frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"


class HabitStatus(StrEnum):
    """Supported habit lifecycle states."""

    ACTIVE = "active"
    ARCHIVED = "archived"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Return the persisted values for an enum class."""
    return [str(member.value) for member in enum_class]


class Habit(Base):
    """A recurring activity tracked by the planner."""

    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(
            "frequency IN ('daily', 'weekly')",
            name="ck_habits_frequency",
        ),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_habits_status",
        ),
        CheckConstraint(
            "length(color) = 7 AND color LIKE '#______'",
            name="ck_habits_color",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[HabitFrequency] = mapped_column(
        SqlEnum(
            HabitFrequency,
            native_enum=False,
            values_callable=enum_values,
        ),
    )
    status: Mapped[HabitStatus] = mapped_column(
        SqlEnum(
            HabitStatus,
            native_enum=False,
            values_callable=enum_values,
        ),
        default=HabitStatus.ACTIVE,
    )
    color: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
    )
    check_ins: Mapped[list["HabitCheckIn"]] = relationship(
        back_populates="habit",
        cascade="all, delete-orphan",
        order_by="HabitCheckIn.check_in_date",
    )


class HabitCheckIn(Base):
    """A completion recorded for one habit on one calendar date."""

    __tablename__ = "habit_check_ins"
    __table_args__ = (
        UniqueConstraint(
            "habit_id",
            "check_in_date",
            name="uq_habit_check_ins_habit_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(
        ForeignKey(
            "habits.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    check_in_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
    )
    habit: Mapped[Habit] = relationship(back_populates="check_ins")
