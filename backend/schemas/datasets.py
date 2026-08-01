import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationDatasetItemRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=100_000)
    expected_output: str | None = Field(default=None, max_length=100_000)
    expected_keywords: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("input_text")
    @classmethod
    def reject_blank_input(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("expected_keywords")
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for keyword in values:
            candidate = keyword.strip()
            identity = candidate.casefold()
            if candidate and identity not in seen:
                normalized.append(candidate)
                seen.add(identity)
        return normalized


class CreateEvaluationDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    items: list[EvaluationDatasetItemRequest] = Field(min_length=1, max_length=10_000)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class EvaluationDatasetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    input_text: str
    expected_output: str | None
    expected_keywords: list[str]
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime


class EvaluationDatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    items: list[EvaluationDatasetItemResponse]
    created_at: datetime
    updated_at: datetime


class AttachEvaluationDatasetRequest(BaseModel):
    dataset_id: uuid.UUID
