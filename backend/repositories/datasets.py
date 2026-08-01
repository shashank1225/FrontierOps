import uuid
from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.dataset import EvaluationDataset
from repositories.base import SQLAlchemyRepository
from repositories.contracts import RepositoryConflictError


class SQLAlchemyEvaluationDatasetRepository(SQLAlchemyRepository[EvaluationDataset]):
    """SQLAlchemy adapter for evaluation dataset persistence."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EvaluationDataset)

    async def add(self, dataset: EvaluationDataset) -> EvaluationDataset:
        try:
            return await super().add(dataset)
        except IntegrityError as error:
            raise RepositoryConflictError from error

    async def get(self, dataset_id: uuid.UUID) -> EvaluationDataset | None:
        statement = (
            select(EvaluationDataset)
            .where(EvaluationDataset.id == dataset_id)
            .options(selectinload(EvaluationDataset.items))
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[EvaluationDataset]:
        statement = (
            select(EvaluationDataset)
            .order_by(EvaluationDataset.created_at.desc(), EvaluationDataset.id)
            .offset(offset)
            .limit(limit)
            .options(selectinload(EvaluationDataset.items))
        )
        return (await self._session.scalars(statement)).all()

    async def exists_by_name(self, name: str) -> bool:
        statement = select(exists().where(EvaluationDataset.name == name))
        return bool(await self._session.scalar(statement))
