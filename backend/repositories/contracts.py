import uuid
from collections.abc import Sequence
from typing import Protocol

from models.application import AIApplication


class ApplicationRepository(Protocol):
    """Persistence port required by application use cases."""

    async def add(self, application: AIApplication) -> AIApplication: ...

    async def get(self, application_id: uuid.UUID) -> AIApplication | None: ...

    async def list(self, *, offset: int, limit: int) -> Sequence[AIApplication]: ...

    async def exists_by_name(self, name: str) -> bool: ...

    async def dataset_exists(self, dataset_id: uuid.UUID) -> bool: ...


class RepositoryConflictError(Exception):
    """Raised when a persistence uniqueness invariant is violated."""
