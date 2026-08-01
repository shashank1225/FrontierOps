import socket

from evaluation.engine import EvaluationEngine
from evaluation.jobs import EvaluationJobQueue
from models.enums import EvaluationRunStatus


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
        await self._queue.mark_running(message.job)
        try:
            run = await self._engine.run(message.job.application_id)
            if run.id is None:
                raise RuntimeError("Evaluation engine returned a run without an identifier.")
            if run.status is EvaluationRunStatus.FAILED:
                error_message = run.error_message or "Evaluation failed."
                await self._queue.mark_failed(message.job, error_message)
            else:
                await self._queue.mark_completed(message.job, run.id)
        except Exception:
            await self._queue.mark_failed(
                message.job, "Evaluation job failed before producing a completed run."
            )
            await self._queue.acknowledge(message)
        else:
            await self._queue.acknowledge(message)
        return True

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
