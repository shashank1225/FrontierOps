import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from evaluation.jobs import EvaluationJob, EvaluationJobQueue, EvaluationJobState
from repositories.contracts import ApplicationRepository
from services.exceptions import ApplicationNotFoundError


class EvaluationJobNotFoundError(Exception):
    def __init__(self, job_id: uuid.UUID) -> None:
        super().__init__(f"Evaluation job '{job_id}' was not found.")


class EvaluationJobService:
    def __init__(
        self,
        applications: ApplicationRepository,
        queue: EvaluationJobQueue,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._applications = applications
        self._queue = queue
        self._clock = clock or (lambda: datetime.now(UTC))

    async def enqueue(self, application_id: uuid.UUID) -> EvaluationJobState:
        application = await self._applications.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        job = EvaluationJob(
            id=uuid.uuid4(), application_id=application_id, enqueued_at=self._clock()
        )
        await self._queue.enqueue(job)
        state = await self._queue.get_state(job.id)
        if state is None:
            raise RuntimeError("Evaluation job state was not persisted.")
        return state

    async def get(self, job_id: uuid.UUID) -> EvaluationJobState:
        state = await self._queue.get_state(job_id)
        if state is None:
            raise EvaluationJobNotFoundError(job_id)
        return state
