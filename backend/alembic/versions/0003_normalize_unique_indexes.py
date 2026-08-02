"""Normalize unique indexes to match SQLAlchemy metadata.

Revision ID: 0003_normalize_unique_indexes
Revises: 0002_add_result_quality_score
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_normalize_unique_indexes"
down_revision: str | None = "0002_add_result_quality_score"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNIQUE_COLUMNS = (
    ("ai_applications", "name"),
    ("evaluation_datasets", "name"),
    ("release_gate_policies", "application_id"),
)


def upgrade() -> None:
    for table, column in UNIQUE_COLUMNS:
        op.drop_constraint(f"uq_{table}_{column}", table, type_="unique")
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.create_index(f"ix_{table}_{column}", table, [column], unique=True)


def downgrade() -> None:
    for table, column in reversed(UNIQUE_COLUMNS):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.create_index(f"ix_{table}_{column}", table, [column])
        op.create_unique_constraint(f"uq_{table}_{column}", table, [column])
