from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import session_scope
from repositories.applications import SQLAlchemyApplicationRepository
from services.applications import ApplicationService
from services.health import HealthService


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]


def get_health_service(session: DatabaseSession, redis: RedisClient) -> HealthService:
    return HealthService(session=session, redis=redis)


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]


def get_application_service(session: DatabaseSession) -> ApplicationService:
    repository = SQLAlchemyApplicationRepository(session)
    return ApplicationService(repository=repository)


ApplicationServiceDependency = Annotated[ApplicationService, Depends(get_application_service)]
