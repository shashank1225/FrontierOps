import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.application import AIApplication
    from models.evaluation import EvaluationRun


class PromptVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("application_id", "version", name="uq_prompt_versions_app_version"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_applications.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    template: Mapped[str] = mapped_column(Text)
    change_summary: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    application: Mapped["AIApplication"] = relationship(
        back_populates="prompt_versions", foreign_keys=[application_id]
    )
    evaluation_runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="prompt_version")
