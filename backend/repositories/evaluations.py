import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from evaluation.history import EvaluationRunFilter
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

    async def list_filtered(
        self, filters: EvaluationRunFilter
    ) -> tuple[Sequence[EvaluationRun], int]:
        conditions = []
        if filters.application_id is not None:
            conditions.append(EvaluationRun.application_id == filters.application_id)
        if filters.created_from is not None:
            conditions.append(EvaluationRun.created_at >= filters.created_from)
        if filters.created_to is not None:
            conditions.append(EvaluationRun.created_at <= filters.created_to)
        if filters.model is not None:
            conditions.append(EvaluationRun.model == filters.model)
        if filters.prompt_version_id is not None:
            conditions.append(EvaluationRun.prompt_version_id == filters.prompt_version_id)
        if filters.status is not None:
            conditions.append(EvaluationRun.status == filters.status)
        if filters.release_decision is not None:
            conditions.append(EvaluationRun.release_decision == filters.release_decision)

        count_statement = select(func.count()).select_from(EvaluationRun).where(*conditions)
        total = int(await self._session.scalar(count_statement) or 0)
        statement = (
            select(EvaluationRun)
            .where(*conditions)
            .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
            .offset(filters.offset)
            .limit(filters.limit)
        )
        return (await self._session.scalars(statement)).all(), total
