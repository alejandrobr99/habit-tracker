"""Add habit direction, finance, and gamification.

Revision ID: 20260808_0002
Revises: 20260808_0001
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0002"
down_revision: str | None = "20260808_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add all tables required by finance and gamification."""
    with op.batch_alter_table("habits") as batch:
        batch.add_column(
            sa.Column("direction", sa.String(length=5), nullable=False, server_default="build"),
        )
        batch.create_check_constraint(
            "ck_habits_direction",
            "direction IN ('build', 'avoid')",
        )

    timestamps = (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "finance_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("minor_unit", sa.Integer(), nullable=False),
        *timestamps,
        sa.CheckConstraint("id = 1", name="ck_finance_settings_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "finance_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("type", sa.String(length=7), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=7), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=120), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["finance_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_transactions_category_id", "finance_transactions", ["category_id"])
    op.create_index("ix_finance_transactions_date", "finance_transactions", ["date"])
    op.create_table(
        "finance_budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("limit_minor", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["finance_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("month", "category_id", name="uq_budgets_month_category"),
    )
    op.create_index("ix_finance_budgets_month", "finance_budgets", ["month"])
    _create_gamification_tables()


def _create_gamification_tables() -> None:
    """Create gamification tables."""
    op.create_table(
        "xp_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_xp_source"),
    )
    op.create_table(
        "badge_awards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("badge_code", sa.String(length=18), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("badge_code"),
    )
    op.create_table(
        "weekly_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("habit_id", sa.Integer(), nullable=True),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start"),
    )
    op.create_table(
        "rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=True),
        sa.Column("cost_xp", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reward_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reward_id", sa.Integer(), nullable=False),
        sa.Column("cost_xp", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=36), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reward_id"], ["rewards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_table(
        "streak_recoveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("habit_id", sa.Integer(), nullable=False),
        sa.Column("recovered_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("habit_id", "recovered_date", name="uq_recovery_habit_date"),
    )
    op.create_index("ix_streak_recoveries_habit_id", "streak_recoveries", ["habit_id"])
    op.create_table(
        "finance_weekly_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start"),
    )


def downgrade() -> None:
    """Remove finance, gamification, and habit direction."""
    op.drop_table("finance_weekly_reviews")
    op.drop_index("ix_streak_recoveries_habit_id", table_name="streak_recoveries")
    op.drop_table("streak_recoveries")
    op.drop_table("reward_redemptions")
    op.drop_table("rewards")
    op.drop_table("weekly_challenges")
    op.drop_table("badge_awards")
    op.drop_table("xp_entries")
    op.drop_index("ix_finance_budgets_month", table_name="finance_budgets")
    op.drop_table("finance_budgets")
    op.drop_index("ix_finance_transactions_date", table_name="finance_transactions")
    op.drop_index(
        "ix_finance_transactions_category_id",
        table_name="finance_transactions",
    )
    op.drop_table("finance_transactions")
    op.drop_table("finance_categories")
    op.drop_table("finance_settings")
    with op.batch_alter_table("habits") as batch:
        batch.drop_constraint("ck_habits_direction", type_="check")
        batch.drop_column("direction")
