import uuid
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock

from redis.asyncio import Redis

from evaluation.redis_queue import RedisEvaluationJobQueue


def fields() -> dict[str, str]:
    return {
        "job_id": str(uuid.uuid4()),
        "application_id": str(uuid.uuid4()),
        "enqueued_at": datetime(2026, 8, 1, tzinfo=UTC).isoformat(),
    }


async def test_consume_reads_new_consumer_group_message() -> None:
    redis = AsyncMock()
    redis.xautoclaim.return_value = ["0-0", [], []]
    message_fields = fields()
    redis.xreadgroup.return_value = [["frontierops:evaluation-jobs", [["1-0", message_fields]]]]
    queue = RedisEvaluationJobQueue(cast(Redis, redis))

    message = await queue.consume("worker-1", block_ms=1)

    assert message is not None
    assert message.stream_id == "1-0"
    assert message.job.id == uuid.UUID(message_fields["job_id"])
    redis.xgroup_create.assert_awaited_once()


async def test_consume_recovers_stale_pending_message_before_new_work() -> None:
    redis = AsyncMock()
    message_fields = fields()
    redis.xautoclaim.return_value = ["0-0", [["2-0", message_fields]], []]
    queue = RedisEvaluationJobQueue(cast(Redis, redis), claim_idle_ms=10)

    message = await queue.consume("worker-2", block_ms=1)

    assert message is not None
    assert message.stream_id == "2-0"
    redis.xreadgroup.assert_not_awaited()
