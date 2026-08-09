"""Create habits and habit check-ins.

Revision ID: 20260808_0001
Revises:
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial planner tables."""
    op.create_table(
        "habits",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "frequency",
            sa.String(length=6),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=8),
            nullable=False,
        ),
        sa.Column(
            "color",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "frequency IN ('daily', 'weekly')",
            name="ck_habits_frequency",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_habits_status",
        ),
        sa.CheckConstraint(
            "length(color) = 7 AND color LIKE '#______'",
            name="ck_habits_color",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "habit_check_ins",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "habit_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "check_in_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["habit_id"],
            ["habits.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "habit_id",
            "check_in_date",
            name="uq_habit_check_ins_habit_date",
        ),
    )
    op.create_index(
        "ix_habit_check_ins_habit_id",
        "habit_check_ins",
        ["habit_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the initial planner tables."""
    op.drop_index(
        "ix_habit_check_ins_habit_id",
        table_name="habit_check_ins",
    )
    op.drop_table("habit_check_ins")
    op.drop_table("habits")
