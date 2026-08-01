import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base


class SQLAlchemyRepository[ModelT: Base]:
    """Reusable persistence mechanics; domain repositories can extend this contract."""

    def __init__(self, session: AsyncSession, model_type: type[ModelT]) -> None:
        self._session = session
        self._model_type = model_type

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self._session.get(self._model_type, entity_id)

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        statement = select(self._model_type).offset(offset).limit(limit)
        return (await self._session.scalars(statement)).all()

    async def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        await self._session.flush()
        return entity
