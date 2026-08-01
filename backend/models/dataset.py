import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from models.evaluation import EvaluationResult, EvaluationRun


class EvaluationDataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_datasets"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(1000))

    items: Mapped[list["EvaluationDatasetItem"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    evaluation_runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="dataset")


class EvaluationDatasetItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_dataset_items"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        index=True,
    )
    input_text: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)
    expected_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    dataset: Mapped["EvaluationDataset"] = relationship(back_populates="items")
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="dataset_item"
    )
