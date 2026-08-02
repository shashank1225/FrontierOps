import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from evaluation.exceptions import PromptRenderingError
from evaluation.prompt_renderer import PromptRenderer


class CreatePromptVersionRequest(BaseModel):
    template: str = Field(min_length=1, max_length=100_000)
    change_summary: str | None = Field(default=None, max_length=2000)

    @field_validator("template")
    @classmethod
    def validate_template(cls, value: str) -> str:
        try:
            PromptRenderer().validate(value)
        except PromptRenderingError as error:
            raise ValueError(str(error)) from error
        return value


class PromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    version: int
    template: str
    change_summary: str | None
    is_active: bool
    created_at: datetime


class PromptVersionComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    baseline_version_id: uuid.UUID
    candidate_version_id: uuid.UUID
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    quality_delta: float | None
    latency_delta_ms: float | None
    latency_delta_percent: float | None
    cost_delta_usd: Decimal
    cost_delta_percent: float | None
    failure_rate_delta: float | None
    regression_detected: bool
    regression_reasons: tuple[str, ...]
