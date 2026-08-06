import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from models.enums import (
    DeploymentStatus,
    EvaluationRunStatus,
    IntegrationSyncStatus,
    ReleaseDecision,
)


class EvaluationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_item_id: uuid.UUID
    response: str | None
    succeeded: bool
    latency_ms: float | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: Decimal
    answer_relevance: float | None
    keyword_coverage: float | None
    hallucination_score: float | None
    quality_score: float | None
    error_message: str | None
    provider_metadata: dict[str, Any]


class EvaluationRunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    prompt_version_id: uuid.UUID
    dataset_id: uuid.UUID
    provider: str
    model: str
    status: EvaluationRunStatus
    release_decision: ReleaseDecision
    deployment_status: DeploymentStatus
    servicenow_incident_number: str | None
    servicenow_sys_id: str | None
    servicenow_sync_status: IntegrationSyncStatus
    report_s3_url: str | None
    started_at: datetime | None
    completed_at: datetime | None
    total_items: int
    successful_items: int
    average_quality_score: float | None
    average_latency_ms: float | None
    failure_rate: float | None
    total_cost_usd: Decimal
    gate_failures: list[dict[str, Any]]
    created_at: datetime


class EvaluationRunDetailResponse(EvaluationRunSummaryResponse):
    error_message: str | None
    results: list[EvaluationResultResponse]


class EvaluationRunPageResponse(BaseModel):
    items: list[EvaluationRunSummaryResponse]
    total: int
    offset: int
    limit: int
