import uuid
from collections.abc import Awaitable
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from evaluation.jobs import (
    EvaluationJob,
    EvaluationJobQueue,
    EvaluationJobState,
    EvaluationJobStatus,
    EvaluationQueueMessage,
)


class RedisEvaluationJobQueue(EvaluationJobQueue):
    stream_name = "frontierops:evaluation-jobs"
    consumer_group = "frontierops-evaluation-workers"
    status_prefix = "frontierops:evaluation-job:"

    def __init__(
        self,
        redis: Redis,
        *,
        status_ttl_seconds: int = 604800,
        claim_idle_ms: int = 60000,
    ) -> None:
        self._redis = redis
        self._status_ttl_seconds = status_ttl_seconds
        self._claim_idle_ms = claim_idle_ms
        self._group_ready = False

    async def enqueue(self, job: EvaluationJob) -> None:
        await self._ensure_group()
        fields = self._job_fields(job)
        async with self._redis.pipeline(transaction=True) as pipeline:
            pipeline.hset(self._status_key(job.id), mapping={**fields, "status": "queued"})
            pipeline.expire(self._status_key(job.id), self._status_ttl_seconds)
            pipeline.xadd(self.stream_name, cast(dict[Any, Any], fields))
            await pipeline.execute()

    async def consume(
        self, consumer: str, *, block_ms: int = 5000
    ) -> EvaluationQueueMessage | None:
        await self._ensure_group()
        stale_message = await self._claim_stale(consumer)
        if stale_message is not None:
            return stale_message
        response = await self._redis.xreadgroup(
            groupname=self.consumer_group,
            consumername=consumer,
            streams={self.stream_name: ">"},
            count=1,
            block=block_ms,
        )
        if not response:
            return None
        _stream, messages = response[0]
        stream_id, fields = messages[0]
        return EvaluationQueueMessage(
            stream_id=str(stream_id),
            job=self._parse_job(cast(dict[str, str], fields)),
        )

    async def _claim_stale(self, consumer: str) -> EvaluationQueueMessage | None:
        response = await self._redis.xautoclaim(
            self.stream_name,
            self.consumer_group,
            consumer,
            min_idle_time=self._claim_idle_ms,
            start_id="0-0",
            count=1,
        )
        messages = response[1]
        if not messages:
            return None
        stream_id, fields = messages[0]
        return EvaluationQueueMessage(
            stream_id=str(stream_id),
            job=self._parse_job(cast(dict[str, str], fields)),
        )

    async def acknowledge(self, message: EvaluationQueueMessage) -> None:
        await self._redis.xack(self.stream_name, self.consumer_group, message.stream_id)

    async def mark_running(self, job: EvaluationJob) -> None:
        await self._update_state(job.id, status=EvaluationJobStatus.RUNNING)

    async def mark_completed(self, job: EvaluationJob, run_id: uuid.UUID) -> None:
        await self._update_state(
            job.id, status=EvaluationJobStatus.COMPLETED, run_id=str(run_id), error_message=""
        )

    async def mark_failed(self, job: EvaluationJob, error_message: str) -> None:
        await self._update_state(
            job.id,
            status=EvaluationJobStatus.FAILED,
            run_id="",
            error_message=error_message[:2000],
        )

    async def get_state(self, job_id: uuid.UUID) -> EvaluationJobState | None:
        lookup = cast(Awaitable[dict[Any, Any]], self._redis.hgetall(self._status_key(job_id)))
        values = cast(dict[str, str], await lookup)
        if not values:
            return None
        return EvaluationJobState(
            id=uuid.UUID(values["job_id"]),
            application_id=uuid.UUID(values["application_id"]),
            status=EvaluationJobStatus(values["status"]),
            enqueued_at=datetime.fromisoformat(values["enqueued_at"]),
            run_id=uuid.UUID(values["run_id"]) if values.get("run_id") else None,
            error_message=values.get("error_message") or None,
        )

    async def _ensure_group(self) -> None:
        if self._group_ready:
            return
        try:
            await self._redis.xgroup_create(
                self.stream_name, self.consumer_group, id="0", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise
        self._group_ready = True

    async def _update_state(self, job_id: uuid.UUID, **values: Any) -> None:
        mapping = {
            key: value.value if isinstance(value, StrEnum) else value
            for key, value in values.items()
        }
        async with self._redis.pipeline(transaction=True) as pipeline:
            pipeline.hset(self._status_key(job_id), mapping=mapping)
            pipeline.expire(self._status_key(job_id), self._status_ttl_seconds)
            await pipeline.execute()

    @staticmethod
    def _job_fields(job: EvaluationJob) -> dict[str, str]:
        return {
            "job_id": str(job.id),
            "application_id": str(job.application_id),
            "enqueued_at": job.enqueued_at.isoformat(),
        }

    @staticmethod
    def _parse_job(fields: dict[str, str]) -> EvaluationJob:
        return EvaluationJob(
            id=uuid.UUID(fields["job_id"]),
            application_id=uuid.UUID(fields["application_id"]),
            enqueued_at=datetime.fromisoformat(fields["enqueued_at"]),
        )

    def _status_key(self, job_id: uuid.UUID) -> str:
        return f"{self.status_prefix}{job_id}"
