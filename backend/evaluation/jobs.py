import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class EvaluationJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class EvaluationJob:
    id: uuid.UUID
    application_id: uuid.UUID
    enqueued_at: datetime


@dataclass(frozen=True, slots=True)
class EvaluationJobState:
    id: uuid.UUID
    application_id: uuid.UUID
    status: EvaluationJobStatus
    enqueued_at: datetime
    run_id: uuid.UUID | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationQueueMessage:
    stream_id: str
    job: EvaluationJob


class EvaluationJobQueue(Protocol):
    async def enqueue(self, job: EvaluationJob) -> None: ...

    async def consume(self, consumer: str, *, block_ms: int) -> EvaluationQueueMessage | None: ...

    async def acknowledge(self, message: EvaluationQueueMessage) -> None: ...

    async def mark_running(self, job: EvaluationJob) -> None: ...

    async def mark_completed(self, job: EvaluationJob, run_id: uuid.UUID) -> None: ...

    async def mark_failed(self, job: EvaluationJob, error_message: str) -> None: ...

    async def get_state(self, job_id: uuid.UUID) -> EvaluationJobState | None: ...
