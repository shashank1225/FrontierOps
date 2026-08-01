import uuid
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock

import pytest

from evaluation.jobs import EvaluationJobQueue, EvaluationJobState, EvaluationJobStatus
from models.application import AIApplication
from repositories.contracts import ApplicationRepository
from services.evaluation_jobs import EvaluationJobNotFoundError, EvaluationJobService


async def test_enqueue_validates_application_and_persists_job_state(
    application_entity: AIApplication,
) -> None:
    applications = AsyncMock()
    queue = AsyncMock()
    applications.get.return_value = application_entity
    now = datetime(2026, 8, 1, tzinfo=UTC)

    async def get_state(job_id: uuid.UUID) -> EvaluationJobState:
        return EvaluationJobState(
            id=job_id,
            application_id=application_entity.id,
            status=EvaluationJobStatus.QUEUED,
            enqueued_at=now,
        )

    queue.get_state.side_effect = get_state
    service = EvaluationJobService(
        cast(ApplicationRepository, applications),
        cast(EvaluationJobQueue, queue),
        clock=lambda: now,
    )

    state = await service.enqueue(application_entity.id)

    assert state.status is EvaluationJobStatus.QUEUED
    queue.enqueue.assert_awaited_once()
    assert queue.enqueue.await_args.args[0].enqueued_at == now


async def test_get_unknown_job_raises_not_found() -> None:
    queue = AsyncMock()
    queue.get_state.return_value = None
    service = EvaluationJobService(
        cast(ApplicationRepository, AsyncMock()), cast(EvaluationJobQueue, queue)
    )

    with pytest.raises(EvaluationJobNotFoundError):
        await service.get(uuid.uuid4())
