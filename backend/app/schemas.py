"""Pydantic request and response schemas."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    BadgeCode,
    FinanceType,
    HabitFrequency,
    HabitKind,
    HabitStatus,
    ResourceStatus,
    UserRole,
    UserStatus,
    XpSourceType,
)

HabitName = Annotated[str, Field(min_length=1, max_length=120)]
HabitColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class HabitCreate(BaseModel):
    """Payload for creating a habit."""

    name: HabitName
    description: str | None = None
    direction: HabitKind = HabitKind.BUILD
    frequency: HabitFrequency
    color: HabitColor

    model_config = ConfigDict(str_strip_whitespace=True)


class HabitUpdate(BaseModel):
    """Payload for partially updating a habit."""

    name: HabitName | None = None
    description: str | None = None
    direction: HabitKind | None = None
    frequency: HabitFrequency | None = None
    status: HabitStatus | None = None
    color: HabitColor | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_explicit_nulls(self) -> Self:
        """Reject nulls for fields that are not nullable in the database."""
        non_nullable_fields = {"name", "direction", "frequency", "status", "color"}
        invalid_fields = non_nullable_fields & self.model_fields_set
        invalid_nulls = sorted(field for field in invalid_fields if getattr(self, field) is None)
        if invalid_nulls:
            field_list = ", ".join(invalid_nulls)
            raise ValueError(f"Fields cannot be null: {field_list}")
        return self


class HabitRead(BaseModel):
    """Habit returned by the API."""

    id: int
    name: str
    description: str | None
    direction: HabitKind
    frequency: HabitFrequency
    status: HabitStatus
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckInRead(BaseModel):
    """Habit check-in returned by the API."""

    id: int
    habit_id: int
    check_in_date: date_type
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HabitWeeklySummary(BaseModel):
    """One habit's activity and streak for a calendar week."""

    habit: HabitRead
    check_in_dates: list[date_type]
    completed_count: int
    target_count: int
    current_streak: int


class WeeklySummaryRead(BaseModel):
    """Weekly summary for all selected habits."""

    week_start: date_type
    week_end: date_type
    habits: list[HabitWeeklySummary]


class HealthRead(BaseModel):
    """Application health status."""

    status: str


Month = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
FinanceName = Annotated[str, Field(min_length=1, max_length=60)]
FinanceColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]
PositiveMoney = Annotated[int, Field(strict=True, gt=0, le=9_223_372_036_854_775_807)]


class FinanceSettingsWrite(BaseModel):
    """Payload for setting the singleton base currency."""

    base_currency: str = Field(min_length=3, max_length=3)

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("base_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Normalize the currency code to uppercase."""
        return value.upper()


class FinanceSettingsRead(BaseModel):
    """Finance settings returned by the API."""

    id: int
    base_currency: str
    minor_unit: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    """Payload for creating a financial category."""

    name: FinanceName
    type: FinanceType
    color: FinanceColor

    model_config = ConfigDict(str_strip_whitespace=True)


class CategoryUpdate(BaseModel):
    """Payload for updating a financial category."""

    name: FinanceName | None = None
    type: FinanceType | None = None
    color: FinanceColor | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def reject_empty_or_null(self) -> Self:
        """Require at least one non-null field."""
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Category fields cannot be null")
        return self


class CategoryRead(BaseModel):
    """Financial category returned by the API."""

    id: int
    name: str
    type: FinanceType
    color: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    """Payload for creating a financial transaction."""

    type: FinanceType
    amount_minor: PositiveMoney
    category_id: int
    date: date_type
    description: Annotated[str, Field(min_length=1, max_length=120)]
    note: Annotated[str, Field(max_length=500)] | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class TransactionUpdate(BaseModel):
    """Payload for partially updating a transaction."""

    type: FinanceType | None = None
    amount_minor: PositiveMoney | None = None
    category_id: int | None = None
    date: date_type | None = None
    description: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    note: Annotated[str, Field(max_length=500)] | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_fields_and_valid_nulls(self) -> Self:
        """Require a field and reject null for non-nullable values."""
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        nullable = {"note"}
        if any(
            getattr(self, field) is None for field in self.model_fields_set if field not in nullable
        ):
            raise ValueError("Transaction fields cannot be null")
        return self


class TransactionRead(BaseModel):
    """Financial transaction returned by the API."""

    id: int
    type: FinanceType
    amount_minor: int
    category_id: int
    date: date_type
    description: str
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetWrite(BaseModel):
    """Payload for creating or replacing a monthly budget."""

    limit_minor: PositiveMoney


class BudgetRead(BaseModel):
    """Monthly budget returned by the API."""

    id: int
    month: str
    category_id: int
    limit_minor: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SummaryCategoryRead(BaseModel):
    """One category row in a monthly summary."""

    category_id: int
    category_name: str
    type: FinanceType
    actual_minor: int
    budget_minor: int | None
    remaining_minor: int | None


class MonthlySummaryRead(BaseModel):
    """Derived financial summary for a calendar month."""

    month: str
    currency: str
    income_minor: int
    expense_minor: int
    balance_minor: int
    budgeted_minor: int
    budget_remaining_minor: int
    categories: list[SummaryCategoryRead]


class XpEntryRead(BaseModel):
    """XP ledger entry returned by the API."""

    id: int
    amount: int
    source_type: XpSourceType
    source_id: str
    occurred_on: date_type
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProgressRead(BaseModel):
    """Calculated XP and level projection."""

    lifetime_xp: int
    available_xp: int
    level: int
    level_start_xp: int
    next_level_xp: int


class BadgeRead(BaseModel):
    """Badge catalog item and award state."""

    code: BadgeCode
    name: str
    description: str
    awarded: bool
    awarded_at: datetime | None


class WeeklyChallengeCreate(BaseModel):
    """Payload for creating a weekly challenge."""

    week_start: date_type
    habit_id: int | None = None
    target_count: Annotated[int, Field(ge=1, le=7)]


class WeeklyChallengeRead(BaseModel):
    """Weekly challenge with projected status and progress."""

    id: int
    week_start: date_type
    habit_id: int | None
    target_count: int
    status: Literal["active", "completed", "expired"]
    progress_count: int
    completed_at: datetime | None
    created_at: datetime


class RewardCreate(BaseModel):
    """Payload for creating a personal reward."""

    name: Annotated[str, Field(min_length=1, max_length=80)]
    description: Annotated[str, Field(max_length=240)] | None = None
    cost_xp: Annotated[int, Field(strict=True, ge=1, le=10_000)]

    model_config = ConfigDict(str_strip_whitespace=True)


class RewardUpdate(BaseModel):
    """Payload for updating a personal reward."""

    name: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    description: Annotated[str, Field(max_length=240)] | None = None
    cost_xp: Annotated[int, Field(strict=True, ge=1, le=10_000)] | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def require_update(self) -> Self:
        """Require at least one field and reject invalid explicit nulls."""
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        nullable = {"description"}
        if any(
            getattr(self, field) is None for field in self.model_fields_set if field not in nullable
        ):
            raise ValueError("Reward fields cannot be null")
        return self


class RewardRead(BaseModel):
    """Personal reward returned by the API."""

    id: int
    name: str
    description: str | None
    cost_xp: int
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RedemptionCreate(BaseModel):
    """Payload for redeeming a reward idempotently."""

    reward_id: int
    idempotency_key: UUID


class RedemptionRead(BaseModel):
    """Reward redemption returned by the API."""

    id: int
    reward_id: int
    cost_xp: int
    idempotency_key: str
    redeemed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StreakRecoveryCreate(BaseModel):
    """Payload for recovering a missing streak date."""

    recovered_date: date_type


class StreakRecoveryRead(BaseModel):
    """Streak recovery returned by the API."""

    id: int
    habit_id: int
    recovered_date: date_type
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinanceWeeklyReviewRead(BaseModel):
    """Weekly finance review returned by the API."""

    id: int
    week_start: date_type
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """Credentials used to create a browser session."""

    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        """Normalize usernames before authentication."""
        return value.strip().lower() if isinstance(value, str) else value


class UserRead(BaseModel):
    """Account metadata visible to its owner or an administrator."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: UserRole
    status: UserStatus
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class PasswordChangeRequest(BaseModel):
    """Credentials required for a user-initiated password change."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    model_config = ConfigDict(extra="forbid")


class AdminUserCreate(BaseModel):
    """Data used by an administrator to provision an account."""

    username: str = Field(
        min_length=3,
        max_length=40,
        pattern=r"^[a-z0-9._-]+$",
    )
    display_name: str = Field(min_length=1, max_length=80)
    temporary_password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.MEMBER

    model_config = ConfigDict(extra="forbid")

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        """Normalize a provisioned username."""
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("display_name", mode="before")
    @classmethod
    def clean_display_name(cls, value: object) -> object:
        """Remove surrounding whitespace from display names."""
        return value.strip() if isinstance(value, str) else value


class AdminUserUpdate(BaseModel):
    """Partial account changes available to an administrator."""

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    role: UserRole | None = None
    status: UserStatus | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("display_name", mode="before")
    @classmethod
    def clean_display_name(cls, value: object) -> object:
        """Remove surrounding whitespace from display names."""
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        """Require at least one account field."""
        if self.display_name is None and self.role is None and self.status is None:
            raise ValueError("At least one field must be provided")
        return self


class AdminPasswordReset(BaseModel):
    """Temporary password selected by an administrator."""

    temporary_password: str = Field(min_length=12, max_length=128)

    model_config = ConfigDict(extra="forbid")
