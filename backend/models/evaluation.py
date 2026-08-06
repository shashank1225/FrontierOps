import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PostgreSQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from models.enums import (
    DeploymentStatus,
    EvaluationRunStatus,
    IntegrationSyncStatus,
    ReleaseDecision,
)

if TYPE_CHECKING:
    from models.application import AIApplication
    from models.dataset import EvaluationDataset, EvaluationDatasetItem
    from models.prompt import PromptVersion


class EvaluationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_runs"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_applications.id", ondelete="CASCADE"), index=True
    )
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_versions.id"), index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_datasets.id"), index=True
    )
    provider: Mapped[str] = mapped_column(index=True)
    model: Mapped[str] = mapped_column(index=True)
    status: Mapped[EvaluationRunStatus] = mapped_column(
        Enum(EvaluationRunStatus, name="evaluation_run_status"),
        default=EvaluationRunStatus.PENDING,
        index=True,
    )
    release_decision: Mapped[ReleaseDecision] = mapped_column(
        Enum(ReleaseDecision, name="release_decision"),
        default=ReleaseDecision.PENDING,
        index=True,
    )
    deployment_status: Mapped[DeploymentStatus] = mapped_column(
        PostgreSQLEnum(DeploymentStatus, name="deployment_status", create_type=False),
        default=DeploymentStatus.EVALUATING,
        index=True,
    )
    servicenow_incident_number: Mapped[str | None] = mapped_column(String(100))
    servicenow_sys_id: Mapped[str | None] = mapped_column(String(100))
    servicenow_sync_status: Mapped[IntegrationSyncStatus] = mapped_column(
        Enum(IntegrationSyncStatus, name="integration_sync_status"),
        default=IntegrationSyncStatus.NOT_REQUIRED,
        index=True,
    )
    report_s3_url: Mapped[str | None] = mapped_column(String(2048))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    successful_items: Mapped[int] = mapped_column(Integer, default=0)
    average_quality_score: Mapped[float | None] = mapped_column(Float)
    average_latency_ms: Mapped[float | None] = mapped_column(Float)
    failure_rate: Mapped[float | None] = mapped_column(Float)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    gate_failures: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    error_message: Mapped[str | None] = mapped_column(Text)

    application: Mapped["AIApplication"] = relationship(back_populates="evaluation_runs")
    prompt_version: Mapped["PromptVersion"] = relationship(back_populates="evaluation_runs")
    dataset: Mapped["EvaluationDataset"] = relationship(back_populates="evaluation_runs")
    results: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    dataset_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_dataset_items.id"), index=True
    )
    response: Mapped[str | None] = mapped_column(Text)
    succeeded: Mapped[bool] = mapped_column(default=False, index=True)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    answer_relevance: Mapped[float | None] = mapped_column(Float)
    keyword_coverage: Mapped[float | None] = mapped_column(Float)
    hallucination_score: Mapped[float | None] = mapped_column(Float)
    quality_score: Mapped[float | None] = mapped_column(Float)
    error_message: Mapped[str | None] = mapped_column(Text)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    run: Mapped["EvaluationRun"] = relationship(back_populates="results")
    dataset_item: Mapped["EvaluationDatasetItem"] = relationship(
        back_populates="evaluation_results"
    )
