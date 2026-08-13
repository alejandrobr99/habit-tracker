"""Add bounded OCR import metadata and per-user cost ledgers.

Revision ID: 20260812_0005
Revises: 20260809_0004
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0005"
down_revision: str | None = "20260809_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create OCR metadata tables without storing document content."""
    op.create_table(
        "finance_ocr_budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("budget_microusd", sa.Integer(), nullable=False),
        sa.Column("reserved_microusd", sa.Integer(), nullable=False),
        sa.Column("spent_microusd", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_finance_ocr_budgets_user_id"),
    )
    op.create_table(
        "finance_ocr_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("document_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_microusd", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "document_hash",
            name="uq_finance_ocr_imports_user_hash",
        ),
    )
    op.create_index(
        "ix_finance_ocr_budgets_user_id",
        "finance_ocr_budgets",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_finance_ocr_imports_user_id",
        "finance_ocr_imports",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove OCR metadata tables."""
    op.drop_index("ix_finance_ocr_imports_user_id", table_name="finance_ocr_imports")
    op.drop_index("ix_finance_ocr_budgets_user_id", table_name="finance_ocr_budgets")
    op.drop_table("finance_ocr_imports")
    op.drop_table("finance_ocr_budgets")
