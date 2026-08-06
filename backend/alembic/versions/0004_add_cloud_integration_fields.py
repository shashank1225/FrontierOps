"""Add AWS report and ServiceNow synchronization fields.

Revision ID: 0004_add_cloud_integration_fields
Revises: 0003_normalize_unique_indexes
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_add_cloud_integration_fields"
down_revision: str | None = "0003_normalize_unique_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    sync_status = sa.Enum(
        "NOT_REQUIRED", "PENDING", "SUCCEEDED", "FAILED", name="integration_sync_status"
    )
    sync_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "evaluation_runs",
        sa.Column(
            "deployment_status",
            postgresql.ENUM(name="deployment_status", create_type=False),
            nullable=False,
            server_default="EVALUATING",
        ),
    )
    op.add_column("evaluation_runs", sa.Column("servicenow_incident_number", sa.String(100)))
    op.add_column("evaluation_runs", sa.Column("servicenow_sys_id", sa.String(100)))
    op.add_column(
        "evaluation_runs",
        sa.Column(
            "servicenow_sync_status", sync_status, nullable=False, server_default="NOT_REQUIRED"
        ),
    )
    op.add_column("evaluation_runs", sa.Column("report_s3_url", sa.String(2048)))
    op.create_index(
        "ix_evaluation_runs_deployment_status", "evaluation_runs", ["deployment_status"]
    )
    op.create_index(
        "ix_evaluation_runs_servicenow_sync_status", "evaluation_runs", ["servicenow_sync_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_runs_servicenow_sync_status", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_deployment_status", table_name="evaluation_runs")
    for column in (
        "report_s3_url",
        "servicenow_sync_status",
        "servicenow_sys_id",
        "servicenow_incident_number",
        "deployment_status",
    ):
        op.drop_column("evaluation_runs", column)
    postgresql.ENUM(name="integration_sync_status").drop(op.get_bind(), checkfirst=True)
