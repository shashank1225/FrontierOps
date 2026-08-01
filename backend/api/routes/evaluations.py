import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from api.dependencies import EvaluationHistoryServiceDependency
from evaluation.history import EvaluationRunFilter
from models.enums import EvaluationRunStatus, ReleaseDecision
from schemas.evaluations import (
    EvaluationRunDetailResponse,
    EvaluationRunPageResponse,
    EvaluationRunSummaryResponse,
)

router = APIRouter()


@router.get("/evaluation-runs/{run_id}", response_model=EvaluationRunDetailResponse)
async def get_evaluation_run(
    run_id: uuid.UUID, service: EvaluationHistoryServiceDependency
) -> EvaluationRunDetailResponse:
    return EvaluationRunDetailResponse.model_validate(await service.get(run_id))


@router.get("/evaluation-runs", response_model=EvaluationRunPageResponse)
async def list_evaluation_runs(
    service: EvaluationHistoryServiceDependency,
    application_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    model: str | None = None,
    prompt_version_id: uuid.UUID | None = None,
    run_status: EvaluationRunStatus | None = None,
    release_decision: ReleaseDecision | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EvaluationRunPageResponse:
    filters = EvaluationRunFilter(
        application_id=application_id,
        created_from=created_from,
        created_to=created_to,
        model=model,
        prompt_version_id=prompt_version_id,
        status=run_status,
        release_decision=release_decision,
        offset=offset,
        limit=limit,
    )
    runs, total = await service.list(filters)
    return EvaluationRunPageResponse(
        items=[EvaluationRunSummaryResponse.model_validate(run) for run in runs],
        total=total,
        offset=offset,
        limit=limit,
    )
