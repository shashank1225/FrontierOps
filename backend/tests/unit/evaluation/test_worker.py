import uuid
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, patch

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


async def test_worker_records_concrete_failure_logs_exception_and_acknowledges() -> None:
    queue = AsyncMock()
    engine = AsyncMock()
    queued_message = message()
    queue.consume.return_value = queued_message
    engine.run.side_effect = RuntimeError("provider connection refused")
    worker = EvaluationWorker(cast(EvaluationJobQueue, queue), cast(EvaluationEngine, engine))

    with patch("evaluation.worker.logger") as worker_logger:
        await worker.run_once(block_ms=1)

    failure = queue.mark_failed.await_args.args[1]
    assert failure == "provider connection refused"
    worker_logger.exception.assert_called_once_with(
        "evaluation_job_failed",
        job_id=str(queued_message.job.id),
        application_id=str(queued_message.job.application_id),
        error_type="RuntimeError",
        exc_info=worker_logger.exception.call_args.kwargs["exc_info"],
    )
    logged_exception = worker_logger.exception.call_args.kwargs["exc_info"][1]
    assert str(logged_exception) == "provider connection refused"
    queue.acknowledge.assert_awaited_once_with(queued_message)


async def test_worker_redacts_credentials_from_failure_state_and_log() -> None:
    queue = AsyncMock()
    engine = AsyncMock()
    queued_message = message()
    queue.consume.return_value = queued_message
    engine.run.side_effect = RuntimeError(
        "failed https://api-user:private-password@example.service-now.com password=hunter2"
    )
    worker = EvaluationWorker(cast(EvaluationJobQueue, queue), cast(EvaluationEngine, engine))

    with patch("evaluation.worker.logger") as worker_logger:
        await worker.run_once(block_ms=1)

    stored_message = queue.mark_failed.await_args.args[1]
    logged_exception = worker_logger.exception.call_args.kwargs["exc_info"][1]
    assert "private-password" not in stored_message
    assert "hunter2" not in stored_message
    assert "private-password" not in str(logged_exception)
    assert "hunter2" not in str(logged_exception)


async def test_worker_returns_false_when_queue_is_empty() -> None:
    queue = AsyncMock()
    queue.consume.return_value = None
    worker = EvaluationWorker(cast(EvaluationJobQueue, queue), cast(EvaluationEngine, AsyncMock()))

    assert await worker.run_once(block_ms=1) is False
