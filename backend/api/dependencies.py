from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.database import session_scope
from evaluation.engine import EvaluationEngine
from evaluation.redis_queue import RedisEvaluationJobQueue
from evaluation.unit_of_work import SQLAlchemyEvaluationUnitOfWorkFactory
from providers.registry import ProviderRegistry
from repositories.applications import SQLAlchemyApplicationRepository
from repositories.datasets import SQLAlchemyEvaluationDatasetRepository
from services.applications import ApplicationService
from services.datasets import EvaluationDatasetService
from services.evaluation_jobs import EvaluationJobService
from services.health import HealthService


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_provider_registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


def get_evaluation_engine(request: Request) -> EvaluationEngine:
    session_factory = cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)
    registry = get_provider_registry(request)
    return EvaluationEngine(
        unit_of_work_factory=SQLAlchemyEvaluationUnitOfWorkFactory(session_factory),
        provider_resolver=registry,
    )


DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]
ProviderRegistryDependency = Annotated[ProviderRegistry, Depends(get_provider_registry)]


def get_health_service(session: DatabaseSession, redis: RedisClient) -> HealthService:
    return HealthService(session=session, redis=redis)


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]


def get_application_service(session: DatabaseSession) -> ApplicationService:
    repository = SQLAlchemyApplicationRepository(session)
    return ApplicationService(repository=repository)


ApplicationServiceDependency = Annotated[ApplicationService, Depends(get_application_service)]


def get_evaluation_dataset_service(session: DatabaseSession) -> EvaluationDatasetService:
    repository = SQLAlchemyEvaluationDatasetRepository(session)
    return EvaluationDatasetService(repository=repository)


EvaluationDatasetServiceDependency = Annotated[
    EvaluationDatasetService, Depends(get_evaluation_dataset_service)
]


def get_evaluation_job_service(
    session: DatabaseSession, redis: RedisClient
) -> EvaluationJobService:
    return EvaluationJobService(
        applications=SQLAlchemyApplicationRepository(session),
        queue=RedisEvaluationJobQueue(redis),
    )


EvaluationJobServiceDependency = Annotated[
    EvaluationJobService, Depends(get_evaluation_job_service)
]
