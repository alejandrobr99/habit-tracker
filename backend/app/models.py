"""SQLAlchemy domain models."""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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


class HabitKind(StrEnum):
    """Supported habit intentions."""

    BUILD = "build"
    AVOID = "avoid"


class FinanceType(StrEnum):
    """Supported financial movement types."""

    INCOME = "income"
    EXPENSE = "expense"


class ResourceStatus(StrEnum):
    """Lifecycle states shared by finance categories and rewards."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class XpSourceType(StrEnum):
    """Events that may produce XP ledger entries."""

    HABIT_CHECK_IN = "habit_check_in"
    WEEKLY_CHALLENGE = "weekly_challenge"
    FINANCE_BUDGET_SETUP = "finance_budget_setup"
    FINANCE_WEEKLY_REVIEW = "finance_weekly_review"
    REWARD_REDEMPTION = "reward_redemption"


class BadgeCode(StrEnum):
    """Stable badge catalog codes."""

    FIRST_STEP = "first_step"
    STEADY_SEVEN = "steady_seven"
    CHALLENGE_COMPLETE = "challenge_complete"
    BUDGET_READY = "budget_ready"
    WEEKLY_REVIEWED = "weekly_reviewed"
    REWARD_CLAIMED = "reward_claimed"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Return the persisted values for an enum class."""
    return [str(member.value) for member in enum_class]


class Habit(Base):
    """A recurring activity tracked by the planner."""

    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('build', 'avoid')",
            name="ck_habits_direction",
        ),
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
    direction: Mapped[HabitKind] = mapped_column(
        SqlEnum(
            HabitKind,
            native_enum=False,
            values_callable=enum_values,
        ),
        default=HabitKind.BUILD,
    )
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


class FinanceSettings(Base):
    """Singleton base-currency settings."""

    __tablename__ = "finance_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_finance_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    base_currency: Mapped[str] = mapped_column(String(3))
    minor_unit: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
    )


class Category(Base):
    """A user-defined financial category."""

    __tablename__ = "finance_categories"
    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_categories_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    type: Mapped[FinanceType] = mapped_column(
        SqlEnum(FinanceType, native_enum=False, values_callable=enum_values),
    )
    color: Mapped[str] = mapped_column(String(7))
    status: Mapped[ResourceStatus] = mapped_column(
        SqlEnum(ResourceStatus, native_enum=False, values_callable=enum_values),
        default=ResourceStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
    )


class FinanceTransaction(Base):
    """A manual income or expense."""

    __tablename__ = "finance_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[FinanceType] = mapped_column(
        SqlEnum(FinanceType, native_enum=False, values_callable=enum_values),
    )
    amount_minor: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[int] = mapped_column(ForeignKey("finance_categories.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
    )


class Budget(Base):
    """A monthly spending limit for one expense category."""

    __tablename__ = "finance_budgets"
    __table_args__ = (UniqueConstraint("month", "category_id", name="uq_budgets_month_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("finance_categories.id"))
    limit_minor: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
    )


class XpEntry(Base):
    """An immutable XP recognition or redemption entry."""

    __tablename__ = "xp_entries"
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_xp_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[XpSourceType] = mapped_column(
        SqlEnum(XpSourceType, native_enum=False, values_callable=enum_values),
    )
    source_id: Mapped[str] = mapped_column(String(100))
    occurred_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class BadgeAward(Base):
    """An idempotent badge award."""

    __tablename__ = "badge_awards"

    id: Mapped[int] = mapped_column(primary_key=True)
    badge_code: Mapped[BadgeCode] = mapped_column(
        SqlEnum(BadgeCode, native_enum=False, values_callable=enum_values),
        unique=True,
    )
    awarded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class WeeklyChallenge(Base):
    """A private weekly check-in challenge."""

    __tablename__ = "weekly_challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True)
    habit_id: Mapped[int | None] = mapped_column(
        ForeignKey("habits.id"),
        nullable=True,
    )
    target_count: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class Reward(Base):
    """A personal reward defined by the user."""

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(240), nullable=True)
    cost_xp: Mapped[int] = mapped_column(Integer)
    status: Mapped[ResourceStatus] = mapped_column(
        SqlEnum(ResourceStatus, native_enum=False, values_callable=enum_values),
        default=ResourceStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
    )


class RewardRedemption(Base):
    """An immutable redemption of a personal reward."""

    __tablename__ = "reward_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"))
    cost_xp: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(36), unique=True)
    redeemed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class StreakRecovery(Base):
    """A recovered missing date used only for streak continuity."""

    __tablename__ = "streak_recoveries"
    __table_args__ = (
        UniqueConstraint("habit_id", "recovered_date", name="uq_recovery_habit_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey("habits.id"), index=True)
    recovered_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class FinanceWeeklyReview(Base):
    """A weekly financial review confirmation without financial details."""

    __tablename__ = "finance_weekly_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
