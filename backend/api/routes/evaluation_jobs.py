import uuid

from fastapi import APIRouter, status

from api.dependencies import EvaluationJobServiceDependency
from schemas.evaluation_jobs import EvaluationJobResponse

router = APIRouter()


@router.post(
    "/applications/{application_id}/evaluations",
    response_model=EvaluationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_evaluation(
    application_id: uuid.UUID, service: EvaluationJobServiceDependency
) -> EvaluationJobResponse:
    return EvaluationJobResponse.model_validate(await service.enqueue(application_id))


@router.get("/evaluation-jobs/{job_id}", response_model=EvaluationJobResponse)
async def get_evaluation_job(
    job_id: uuid.UUID, service: EvaluationJobServiceDependency
) -> EvaluationJobResponse:
    return EvaluationJobResponse.model_validate(await service.get(job_id))
