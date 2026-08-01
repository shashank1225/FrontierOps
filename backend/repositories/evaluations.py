import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.evaluation import EvaluationResult, EvaluationRun
from repositories.base import SQLAlchemyRepository


class SQLAlchemyEvaluationRunRepository(SQLAlchemyRepository[EvaluationRun]):
    """SQLAlchemy adapter for evaluation run and result persistence."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvaluationRun)

    async def save(self, run: EvaluationRun) -> EvaluationRun:
        self._session.add(run)
        await self._session.flush()
        return run

    async def add_result(self, result: EvaluationResult) -> EvaluationResult:
        self._session.add(result)
        await self._session.flush()
        return result

    async def get(self, run_id: uuid.UUID) -> EvaluationRun | None:
        statement = (
            select(EvaluationRun)
            .where(EvaluationRun.id == run_id)
            .options(selectinload(EvaluationRun.results))
        )
        return (await self._session.scalars(statement)).one_or_none()
