"""Enforce one streak recovery per habit and month.

Revision ID: 20260808_0003
Revises: 20260808_0002
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0003"
down_revision: str | None = "20260808_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist the recovery month and enforce its uniqueness."""
    with op.batch_alter_table("streak_recoveries") as batch:
        batch.add_column(sa.Column("recovery_month", sa.String(length=7), nullable=True))

    op.execute(
        sa.text(
            "UPDATE streak_recoveries "
            "SET recovery_month = substr(CAST(recovered_date AS VARCHAR), 1, 7)",
        ),
    )
    op.execute(
        sa.text(
            "DELETE FROM streak_recoveries "
            "WHERE id NOT IN ("
            "SELECT MIN(id) FROM streak_recoveries GROUP BY habit_id, recovery_month"
            ")",
        ),
    )

    with op.batch_alter_table("streak_recoveries") as batch:
        batch.alter_column("recovery_month", existing_type=sa.String(length=7), nullable=False)
        batch.create_unique_constraint(
            "uq_recovery_habit_month",
            ["habit_id", "recovery_month"],
        )


def downgrade() -> None:
    """Remove the recovery-month uniqueness guarantee."""
    with op.batch_alter_table("streak_recoveries") as batch:
        batch.drop_constraint("uq_recovery_habit_month", type_="unique")
        batch.drop_column("recovery_month")
