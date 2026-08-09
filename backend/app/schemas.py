"""Pydantic request and response schemas."""

from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import HabitFrequency, HabitStatus

HabitName = Annotated[str, Field(min_length=1, max_length=120)]
HabitColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


class HabitCreate(BaseModel):
    """Payload for creating a habit."""

    name: HabitName
    description: str | None = None
    frequency: HabitFrequency
    color: HabitColor

    model_config = ConfigDict(str_strip_whitespace=True)


class HabitUpdate(BaseModel):
    """Payload for partially updating a habit."""

    name: HabitName | None = None
    description: str | None = None
    frequency: HabitFrequency | None = None
    status: HabitStatus | None = None
    color: HabitColor | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_explicit_nulls(self) -> Self:
        """Reject nulls for fields that are not nullable in the database."""
        non_nullable_fields = {"name", "frequency", "status", "color"}
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
    check_in_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HabitWeeklySummary(BaseModel):
    """One habit's activity and streak for a calendar week."""

    habit: HabitRead
    check_in_dates: list[date]
    completed_count: int
    target_count: int
    current_streak: int


class WeeklySummaryRead(BaseModel):
    """Weekly summary for all selected habits."""

    week_start: date
    week_end: date
    habits: list[HabitWeeklySummary]


class HealthRead(BaseModel):
    """Application health status."""

    status: str
