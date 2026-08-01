import uuid
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock

from evaluation.engine import EvaluationEngine
from evaluation.jobs import EvaluationJob, EvaluationJobQueue, EvaluationQueueMessage
from evaluation.worker import EvaluationWorker
from models.enums import EvaluationRunStatus
from models.evaluation import EvaluationRun


def message() -> EvaluationQueueMessage:
    return EvaluationQueueMessage(
        stream_id="1-0",
        job=EvaluationJob(
            id=uuid.uuid4(),
            application_id=uuid.uuid4(),
            enqueued_at=datetime(2026, 8, 1, tzinfo=UTC),
        ),
    )


async def test_worker_completes_and_acknowledges_job() -> None:
    queue = AsyncMock()
    engine = AsyncMock()
    queued_message = message()
    queue.consume.return_value = queued_message
    run = EvaluationRun(id=uuid.uuid4(), status=EvaluationRunStatus.COMPLETED)
    engine.run.return_value = run
    worker = EvaluationWorker(
        cast(EvaluationJobQueue, queue),
        cast(EvaluationEngine, engine),
        consumer_name="test-worker",
    )

    processed = await worker.run_once(block_ms=1)

    assert processed is True
    queue.mark_running.assert_awaited_once_with(queued_message.job)
    queue.mark_completed.assert_awaited_once_with(queued_message.job, run.id)
    queue.acknowledge.assert_awaited_once_with(queued_message)


async def test_worker_records_sanitized_failure_and_acknowledges() -> None:
    queue = AsyncMock()
    engine = AsyncMock()
    queued_message = message()
    queue.consume.return_value = queued_message
    engine.run.side_effect = RuntimeError("secret")
    worker = EvaluationWorker(cast(EvaluationJobQueue, queue), cast(EvaluationEngine, engine))

    await worker.run_once(block_ms=1)

    failure = queue.mark_failed.await_args.args[1]
    assert "secret" not in failure
    queue.acknowledge.assert_awaited_once_with(queued_message)


async def test_worker_returns_false_when_queue_is_empty() -> None:
    queue = AsyncMock()
    queue.consume.return_value = None
    worker = EvaluationWorker(cast(EvaluationJobQueue, queue), cast(EvaluationEngine, AsyncMock()))

    assert await worker.run_once(block_ms=1) is False
