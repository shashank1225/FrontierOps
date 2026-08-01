"""Create the initial FrontierOps domain schema.

Revision ID: 0001_initial_schema
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

deployment_status = sa.Enum(
    "DRAFT",
    "EVALUATING",
    "APPROVED",
    "BLOCKED",
    "DEPLOYED",
    "ARCHIVED",
    name="deployment_status",
)
evaluation_run_status = sa.Enum(
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    name="evaluation_run_status",
)
release_decision = sa.Enum("PENDING", "APPROVED", "BLOCKED", name="release_decision")


def _identity_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        *_identity_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_datasets"),
        sa.UniqueConstraint("name", name="uq_evaluation_datasets_name"),
    )
    op.create_index("ix_evaluation_datasets_name", "evaluation_datasets", ["name"])

    op.create_table(
        "ai_applications",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("deployment_status", deployment_status, nullable=False),
        sa.Column("active_prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evaluation_dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_identity_columns(),
        sa.ForeignKeyConstraint(
            ["evaluation_dataset_id"],
            ["evaluation_datasets.id"],
            name="fk_ai_applications_evaluation_dataset_id_evaluation_datasets",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_applications"),
        sa.UniqueConstraint("name", name="uq_ai_applications_name"),
    )
    for column in ("name", "provider", "model", "deployment_status"):
        op.create_index(f"ix_ai_applications_{column}", "ai_applications", [column])

    op.create_table(
        "prompt_versions",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["ai_applications.id"],
            name="fk_prompt_versions_application_id_ai_applications",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_prompt_versions"),
        sa.UniqueConstraint("application_id", "version", name="uq_prompt_versions_app_version"),
    )
    op.create_index("ix_prompt_versions_application_id", "prompt_versions", ["application_id"])
    op.create_index("ix_prompt_versions_is_active", "prompt_versions", ["is_active"])
    op.create_foreign_key(
        "fk_ai_applications_active_prompt_version_id_prompt_versions",
        "ai_applications",
        "prompt_versions",
        ["active_prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "evaluation_dataset_items",
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("expected_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["evaluation_datasets.id"],
            name="fk_evaluation_dataset_items_dataset_id_evaluation_datasets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_dataset_items"),
    )
    op.create_index(
        "ix_evaluation_dataset_items_dataset_id", "evaluation_dataset_items", ["dataset_id"]
    )

    op.create_table(
        "release_gate_policies",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("minimum_quality_score", sa.Float(), nullable=False),
        sa.Column("maximum_latency_ms", sa.Float(), nullable=False),
        sa.Column("maximum_failure_rate", sa.Float(), nullable=False),
        sa.Column("maximum_cost_usd", sa.Float(), nullable=True),
        *_identity_columns(),
        sa.CheckConstraint(
            "maximum_failure_rate >= 0 AND maximum_failure_rate <= 1",
            name="ck_release_gate_policies_failure_rate_range",
        ),
        sa.CheckConstraint(
            "maximum_latency_ms > 0", name="ck_release_gate_policies_positive_latency"
        ),
        sa.CheckConstraint(
            "minimum_quality_score >= 0 AND minimum_quality_score <= 1",
            name="ck_release_gate_policies_quality_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["ai_applications.id"],
            name="fk_release_gate_policies_application_id_ai_applications",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_release_gate_policies"),
        sa.UniqueConstraint("application_id", name="uq_release_gate_policies_application_id"),
    )
    op.create_index(
        "ix_release_gate_policies_application_id", "release_gate_policies", ["application_id"]
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("status", evaluation_run_status, nullable=False),
        sa.Column("release_decision", release_decision, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("successful_items", sa.Integer(), nullable=False),
        sa.Column("average_quality_score", sa.Float(), nullable=True),
        sa.Column("average_latency_ms", sa.Float(), nullable=True),
        sa.Column("failure_rate", sa.Float(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("gate_failures", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_identity_columns(),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["ai_applications.id"],
            name="fk_evaluation_runs_application_id_ai_applications",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["evaluation_datasets.id"],
            name="fk_evaluation_runs_dataset_id_evaluation_datasets",
        ),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"],
            ["prompt_versions.id"],
            name="fk_evaluation_runs_prompt_version_id_prompt_versions",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_runs"),
    )
    for column in (
        "application_id",
        "prompt_version_id",
        "dataset_id",
        "provider",
        "model",
        "status",
        "release_decision",
    ):
        op.create_index(f"ix_evaluation_runs_{column}", "evaluation_runs", [column])

    op.create_table(
        "evaluation_results",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("answer_relevance", sa.Float(), nullable=True),
        sa.Column("keyword_coverage", sa.Float(), nullable=True),
        sa.Column("hallucination_score", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *_identity_columns(),
        sa.ForeignKeyConstraint(
            ["dataset_item_id"],
            ["evaluation_dataset_items.id"],
            name="fk_evaluation_results_dataset_item_id_evaluation_dataset_items",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["evaluation_runs.id"],
            name="fk_evaluation_results_run_id_evaluation_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_results"),
    )
    for column in ("run_id", "dataset_item_id", "succeeded"):
        op.create_index(f"ix_evaluation_results_{column}", "evaluation_results", [column])


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("release_gate_policies")
    op.drop_table("evaluation_dataset_items")
    op.drop_constraint(
        "fk_ai_applications_active_prompt_version_id_prompt_versions",
        "ai_applications",
        type_="foreignkey",
    )
    op.drop_table("prompt_versions")
    op.drop_table("ai_applications")
    op.drop_table("evaluation_datasets")
    release_decision.drop(op.get_bind(), checkfirst=True)
    evaluation_run_status.drop(op.get_bind(), checkfirst=True)
    deployment_status.drop(op.get_bind(), checkfirst=True)
