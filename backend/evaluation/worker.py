import re
import socket

import structlog
from opentelemetry import trace

from evaluation.engine import EvaluationEngine
from evaluation.jobs import EvaluationJobQueue
from models.enums import EvaluationRunStatus
from observability.metrics import WORKER_JOBS

tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)

_URL_CREDENTIALS = re.compile(r"(https?://)[^\s/:@]+:[^\s/@]+@", re.IGNORECASE)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"\b(password|passwd|pwd|token|api[_-]?key|secret|authorization)=([^\s&]+)",
    re.IGNORECASE,
)


def _safe_error_message(error: Exception) -> str:
    message = str(error).strip() or type(error).__name__
    message = _URL_CREDENTIALS.sub(r"\1[REDACTED]@", message)
    return _SENSITIVE_ASSIGNMENT.sub(r"\1=[REDACTED]", message)[:2000]


class EvaluationWorker:
    def __init__(
        self,
        queue: EvaluationJobQueue,
        engine: EvaluationEngine,
        *,
        consumer_name: str | None = None,
    ) -> None:
        self._queue = queue
        self._engine = engine
        self._consumer_name = consumer_name or socket.gethostname()

    async def run_once(self, *, block_ms: int = 5000) -> bool:
        message = await self._queue.consume(self._consumer_name, block_ms=block_ms)
        if message is None:
            return False
        with tracer.start_as_current_span(
            "evaluation.worker.job",
            attributes={
                "frontierops.job.id": str(message.job.id),
                "frontierops.application.id": str(message.job.application_id),
            },
        ):
            await self._queue.mark_running(message.job)
            try:
                run = await self._engine.run(message.job.application_id)
                if run.id is None:
                    raise RuntimeError("Evaluation engine returned a run without an identifier.")
                if run.status is EvaluationRunStatus.FAILED:
                    error_message = run.error_message or "Evaluation failed."
                    await self._queue.mark_failed(message.job, error_message)
                    WORKER_JOBS.labels("failed").inc()
                else:
                    await self._queue.mark_completed(message.job, run.id)
                    WORKER_JOBS.labels("completed").inc()
            except Exception as error:
                error_message = _safe_error_message(error)
                safe_error = RuntimeError(error_message)
                logger.exception(
                    "evaluation_job_failed",
                    job_id=str(message.job.id),
                    application_id=str(message.job.application_id),
                    error_type=type(error).__name__,
                    exc_info=(type(safe_error), safe_error, error.__traceback__),
                )
                await self._queue.mark_failed(message.job, error_message)
                WORKER_JOBS.labels("failed").inc()
                await self._queue.acknowledge(message)
            else:
                await self._queue.acknowledge(message)
        return True

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
