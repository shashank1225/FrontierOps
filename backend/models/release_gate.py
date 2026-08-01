import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.application import AIApplication


class ReleaseGatePolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "release_gate_policies"
    __table_args__ = (
        CheckConstraint(
            "minimum_quality_score >= 0 AND minimum_quality_score <= 1",
            name="quality_score_range",
        ),
        CheckConstraint("maximum_latency_ms > 0", name="positive_latency"),
        CheckConstraint(
            "maximum_failure_rate >= 0 AND maximum_failure_rate <= 1",
            name="failure_rate_range",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_applications.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    minimum_quality_score: Mapped[float] = mapped_column(Float, default=0.75)
    maximum_latency_ms: Mapped[float] = mapped_column(Float, default=5000.0)
    maximum_failure_rate: Mapped[float] = mapped_column(Float, default=0.05)
    maximum_cost_usd: Mapped[float | None] = mapped_column(Float)

    application: Mapped["AIApplication"] = relationship(back_populates="release_gate_policy")
