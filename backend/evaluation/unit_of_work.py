from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from repositories.applications import SQLAlchemyApplicationRepository
from repositories.contracts import (
    ApplicationRepository,
    EvaluationDatasetRepository,
    EvaluationRunRepository,
)
from repositories.datasets import SQLAlchemyEvaluationDatasetRepository
from repositories.evaluations import SQLAlchemyEvaluationRunRepository


class EvaluationUnitOfWork(Protocol):
    applications: ApplicationRepository
    datasets: EvaluationDatasetRepository
    runs: EvaluationRunRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


class EvaluationUnitOfWorkFactory(Protocol):
    def __call__(self) -> EvaluationUnitOfWork: ...


class SQLAlchemyEvaluationUnitOfWork:
    """Transaction boundary optimized for checkpointed, long-running evaluations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.applications: ApplicationRepository
        self.datasets: EvaluationDatasetRepository
        self.runs: EvaluationRunRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.applications = SQLAlchemyApplicationRepository(self._session)
        self.datasets = SQLAlchemyEvaluationDatasetRepository(self._session)
        self.runs = SQLAlchemyEvaluationRunRepository(self._session)
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exception is not None:
            await self._session.rollback()
        await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")
        await self._session.commit()


class SQLAlchemyEvaluationUnitOfWorkFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> EvaluationUnitOfWork:
        return SQLAlchemyEvaluationUnitOfWork(self._session_factory)
