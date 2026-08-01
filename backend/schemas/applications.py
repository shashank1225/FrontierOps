import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import DeploymentStatus


class RegisterApplicationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=255)
    prompt_template: str = Field(min_length=1, max_length=100_000)
    prompt_change_summary: str | None = Field(default=None, max_length=2000)
    evaluation_dataset_id: uuid.UUID | None = None

    @field_validator("name", "provider", "model", "prompt_template")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class PromptVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    template: str
    change_summary: str | None
    is_active: bool
    created_at: datetime


class ReleaseGatePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    minimum_quality_score: float
    maximum_latency_ms: float
    maximum_failure_rate: float
    maximum_cost_usd: float | None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    provider: str
    model: str
    deployment_status: DeploymentStatus
    evaluation_dataset_id: uuid.UUID | None
    active_prompt_version: PromptVersionSummary
    release_gate_policy: ReleaseGatePolicyResponse
    created_at: datetime
    updated_at: datetime
