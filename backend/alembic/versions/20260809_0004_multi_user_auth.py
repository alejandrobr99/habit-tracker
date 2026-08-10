"""Add private users, sessions, and resource ownership.

Revision ID: 20260809_0004
Revises: 20260808_0003
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260809_0004"
down_revision: str | None = "20260808_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}
OWNER_TABLES = (
    "habits",
    "finance_categories",
    "finance_transactions",
    "rewards",
)


def upgrade() -> None:
    """Create accounts and assign all existing data to the initial administrator."""
    _create_identity_tables()
    for table_name in OWNER_TABLES:
        _add_owner(table_name)
    _migrate_finance_settings()
    _migrate_budgets()
    _migrate_xp_entries()
    _migrate_badge_awards()
    _migrate_weekly_challenges()
    _migrate_reward_redemptions()
    _migrate_finance_reviews()


def _create_identity_tables() -> None:
    """Create user and session tables with an unusable bootstrap administrator."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=6), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_users_role"),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_users_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.execute(
        sa.text(
            "INSERT INTO users "
            "(id, username, display_name, password_hash, role, status, "
            "must_change_password, created_at, updated_at) "
            "VALUES (1, 'admin', 'Administrador', '!', 'admin', 'active', "
            "1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        ),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])


def _add_owner(table_name: str) -> None:
    """Add and backfill a standard user ownership column."""
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute(sa.text(f"UPDATE {table_name} SET user_id = 1"))
    with op.batch_alter_table(table_name) as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            f"fk_{table_name}_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_index(f"ix_{table_name}_user_id", ["user_id"])


def _migrate_finance_settings() -> None:
    """Replace the global singleton with one settings row per user."""
    with op.batch_alter_table("finance_settings") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("ck_finance_settings_singleton", type_="check")
    op.execute(sa.text("UPDATE finance_settings SET user_id = 1"))
    with op.batch_alter_table("finance_settings") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_finance_settings_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint("uq_finance_settings_user", ["user_id"])
        batch.create_index("ix_finance_settings_user_id", ["user_id"])


def _migrate_budgets() -> None:
    """Scope monthly category budgets to their owner."""
    with op.batch_alter_table("finance_budgets") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_budgets_month_category", type_="unique")
    op.execute(sa.text("UPDATE finance_budgets SET user_id = 1"))
    with op.batch_alter_table("finance_budgets") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_finance_budgets_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_budgets_user_month_category",
            ["user_id", "month", "category_id"],
        )
        batch.create_index("ix_finance_budgets_user_id", ["user_id"])


def _migrate_xp_entries() -> None:
    """Scope idempotent XP sources to their owner."""
    with op.batch_alter_table("xp_entries") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_xp_source", type_="unique")
    op.execute(sa.text("UPDATE xp_entries SET user_id = 1"))
    with op.batch_alter_table("xp_entries") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_xp_entries_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_xp_user_source",
            ["user_id", "source_type", "source_id"],
        )
        batch.create_index("ix_xp_entries_user_id", ["user_id"])


def _migrate_badge_awards() -> None:
    """Allow each user to earn every badge once."""
    with op.batch_alter_table(
        "badge_awards",
        naming_convention=NAMING_CONVENTION,
    ) as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_badge_awards_badge_code", type_="unique")
    op.execute(sa.text("UPDATE badge_awards SET user_id = 1"))
    with op.batch_alter_table("badge_awards") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_badge_awards_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_badge_awards_user_code",
            ["user_id", "badge_code"],
        )
        batch.create_index("ix_badge_awards_user_id", ["user_id"])


def _migrate_weekly_challenges() -> None:
    """Allow one challenge per user and week."""
    with op.batch_alter_table(
        "weekly_challenges",
        naming_convention=NAMING_CONVENTION,
    ) as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_weekly_challenges_week_start", type_="unique")
    op.execute(sa.text("UPDATE weekly_challenges SET user_id = 1"))
    with op.batch_alter_table("weekly_challenges") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_weekly_challenges_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_weekly_challenges_user_week",
            ["user_id", "week_start"],
        )
        batch.create_index("ix_weekly_challenges_user_id", ["user_id"])


def _migrate_reward_redemptions() -> None:
    """Scope redemption idempotency keys to their owner."""
    with op.batch_alter_table(
        "reward_redemptions",
        naming_convention=NAMING_CONVENTION,
    ) as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_reward_redemptions_idempotency_key", type_="unique")
    op.execute(sa.text("UPDATE reward_redemptions SET user_id = 1"))
    with op.batch_alter_table("reward_redemptions") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_reward_redemptions_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_reward_redemptions_user_key",
            ["user_id", "idempotency_key"],
        )
        batch.create_index("ix_reward_redemptions_user_id", ["user_id"])


def _migrate_finance_reviews() -> None:
    """Allow one financial review per user and week."""
    with op.batch_alter_table(
        "finance_weekly_reviews",
        naming_convention=NAMING_CONVENTION,
    ) as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.drop_constraint("uq_finance_weekly_reviews_week_start", type_="unique")
    op.execute(sa.text("UPDATE finance_weekly_reviews SET user_id = 1"))
    with op.batch_alter_table("finance_weekly_reviews") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_finance_weekly_reviews_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_unique_constraint(
            "uq_finance_weekly_reviews_user_week",
            ["user_id", "week_start"],
        )
        batch.create_index("ix_finance_weekly_reviews_user_id", ["user_id"])


def downgrade() -> None:
    """Remove account ownership when global uniqueness can be restored safely."""
    _downgrade_finance_reviews()
    _downgrade_reward_redemptions()
    _downgrade_weekly_challenges()
    _downgrade_badge_awards()
    _downgrade_xp_entries()
    _downgrade_budgets()
    _downgrade_finance_settings()
    for table_name in reversed(OWNER_TABLES):
        _remove_owner(table_name)
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")


def _remove_owner(table_name: str) -> None:
    """Remove a standard owner column."""
    with op.batch_alter_table(table_name) as batch:
        batch.drop_index(f"ix_{table_name}_user_id")
        batch.drop_constraint(f"fk_{table_name}_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")


def _downgrade_finance_settings() -> None:
    with op.batch_alter_table("finance_settings") as batch:
        batch.drop_index("ix_finance_settings_user_id")
        batch.drop_constraint("uq_finance_settings_user", type_="unique")
        batch.drop_constraint("fk_finance_settings_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_check_constraint("ck_finance_settings_singleton", "id = 1")


def _downgrade_budgets() -> None:
    with op.batch_alter_table("finance_budgets") as batch:
        batch.drop_index("ix_finance_budgets_user_id")
        batch.drop_constraint("uq_budgets_user_month_category", type_="unique")
        batch.drop_constraint("fk_finance_budgets_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_unique_constraint(
            "uq_budgets_month_category",
            ["month", "category_id"],
        )


def _downgrade_xp_entries() -> None:
    with op.batch_alter_table("xp_entries") as batch:
        batch.drop_index("ix_xp_entries_user_id")
        batch.drop_constraint("uq_xp_user_source", type_="unique")
        batch.drop_constraint("fk_xp_entries_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_unique_constraint("uq_xp_source", ["source_type", "source_id"])


def _downgrade_badge_awards() -> None:
    with op.batch_alter_table("badge_awards") as batch:
        batch.drop_index("ix_badge_awards_user_id")
        batch.drop_constraint("uq_badge_awards_user_code", type_="unique")
        batch.drop_constraint("fk_badge_awards_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_unique_constraint("uq_badge_awards_badge_code", ["badge_code"])


def _downgrade_weekly_challenges() -> None:
    with op.batch_alter_table("weekly_challenges") as batch:
        batch.drop_index("ix_weekly_challenges_user_id")
        batch.drop_constraint("uq_weekly_challenges_user_week", type_="unique")
        batch.drop_constraint("fk_weekly_challenges_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_unique_constraint("uq_weekly_challenges_week_start", ["week_start"])


def _downgrade_reward_redemptions() -> None:
    with op.batch_alter_table("reward_redemptions") as batch:
        batch.drop_index("ix_reward_redemptions_user_id")
        batch.drop_constraint("uq_reward_redemptions_user_key", type_="unique")
        batch.drop_constraint("fk_reward_redemptions_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_unique_constraint(
            "uq_reward_redemptions_idempotency_key",
            ["idempotency_key"],
        )


def _downgrade_finance_reviews() -> None:
    with op.batch_alter_table("finance_weekly_reviews") as batch:
        batch.drop_index("ix_finance_weekly_reviews_user_id")
        batch.drop_constraint("uq_finance_weekly_reviews_user_week", type_="unique")
        batch.drop_constraint("fk_finance_weekly_reviews_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_unique_constraint(
            "uq_finance_weekly_reviews_week_start",
            ["week_start"],
        )
