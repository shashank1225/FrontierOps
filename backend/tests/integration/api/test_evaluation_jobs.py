import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from httpx import AsyncClient

from evaluation.jobs import EvaluationJobState, EvaluationJobStatus
from services.evaluation_jobs import EvaluationJobNotFoundError


async def test_enqueue_evaluation_returns_accepted(
    client: AsyncClient, evaluation_job_service: AsyncMock
) -> None:
    application_id = uuid.uuid4()
    state = EvaluationJobState(
        id=uuid.uuid4(),
        application_id=application_id,
        status=EvaluationJobStatus.QUEUED,
        enqueued_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    evaluation_job_service.enqueue.return_value = state

    response = await client.post(f"/api/v1/applications/{application_id}/evaluations")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["id"] == str(state.id)


async def test_get_unknown_evaluation_job_returns_not_found(
    client: AsyncClient, evaluation_job_service: AsyncMock
) -> None:
    job_id = uuid.uuid4()
    evaluation_job_service.get.side_effect = EvaluationJobNotFoundError(job_id)

    response = await client.get(f"/api/v1/evaluation-jobs/{job_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "evaluation_job_not_found"
