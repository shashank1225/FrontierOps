from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.health import ReadinessResponse


class HealthService:
    """Infrastructure readiness use case kept outside the HTTP transport layer."""

    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis

    async def readiness(self) -> ReadinessResponse:
        database_ready = await self._database_ready()
        redis_ready = await self._redis_ready()
        return ReadinessResponse(
            status="ready" if database_ready and redis_ready else "not_ready",
            database=database_ready,
            redis=redis_ready,
        )

    async def _database_ready(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    async def _redis_ready(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False
