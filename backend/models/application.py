import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from models.enums import DeploymentStatus

if TYPE_CHECKING:
    from models.dataset import EvaluationDataset
    from models.evaluation import EvaluationRun
    from models.prompt import PromptVersion
    from models.release_gate import ReleaseGatePolicy


class AIApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_applications"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    provider: Mapped[str] = mapped_column(String(100), index=True)
    model: Mapped[str] = mapped_column(String(255), index=True)
    deployment_status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, name="deployment_status"),
        default=DeploymentStatus.DRAFT,
        index=True,
    )
    active_prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_versions.id", ondelete="SET NULL")
    )
    evaluation_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_datasets.id", ondelete="SET NULL")
    )

    prompt_versions: Mapped[list["PromptVersion"]] = relationship(
        back_populates="application",
        foreign_keys="PromptVersion.application_id",
        cascade="all, delete-orphan",
    )
    active_prompt_version: Mapped["PromptVersion | None"] = relationship(
        foreign_keys=[active_prompt_version_id], post_update=True
    )
    evaluation_dataset: Mapped["EvaluationDataset | None"] = relationship()
    release_gate_policy: Mapped["ReleaseGatePolicy | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False
    )
    evaluation_runs: Mapped[list["EvaluationRun"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
