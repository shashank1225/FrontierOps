import uuid
from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.application import AIApplication
from models.dataset import EvaluationDataset
from repositories.base import SQLAlchemyRepository
from repositories.contracts import RepositoryConflictError


class SQLAlchemyApplicationRepository(SQLAlchemyRepository[AIApplication]):
    """SQLAlchemy adapter for the application persistence port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AIApplication)

    async def add(self, application: AIApplication) -> AIApplication:
        try:
            return await super().add(application)
        except IntegrityError as error:
            raise RepositoryConflictError from error

    async def get(self, application_id: uuid.UUID) -> AIApplication | None:
        statement = (
            select(AIApplication)
            .where(AIApplication.id == application_id)
            .options(
                selectinload(AIApplication.active_prompt_version),
                selectinload(AIApplication.release_gate_policy),
            )
        )
        return (await self._session.scalars(statement)).one_or_none()

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[AIApplication]:
        statement = (
            select(AIApplication)
            .order_by(AIApplication.created_at.desc(), AIApplication.id)
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(AIApplication.active_prompt_version),
                selectinload(AIApplication.release_gate_policy),
            )
        )
        return (await self._session.scalars(statement)).all()

    async def exists_by_name(self, name: str) -> bool:
        statement = select(exists().where(AIApplication.name == name))
        return bool(await self._session.scalar(statement))

    async def dataset_exists(self, dataset_id: uuid.UUID) -> bool:
        statement = select(exists().where(EvaluationDataset.id == dataset_id))
        return bool(await self._session.scalar(statement))
