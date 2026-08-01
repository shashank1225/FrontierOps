import uuid
from collections.abc import Sequence
from typing import Protocol

from models.application import AIApplication
from models.dataset import EvaluationDataset


class ApplicationRepository(Protocol):
    """Persistence port required by application use cases."""

    async def add(self, application: AIApplication) -> AIApplication: ...

    async def get(self, application_id: uuid.UUID) -> AIApplication | None: ...

    async def list(self, *, offset: int, limit: int) -> Sequence[AIApplication]: ...

    async def exists_by_name(self, name: str) -> bool: ...

    async def dataset_exists(self, dataset_id: uuid.UUID) -> bool: ...

    async def save(self, application: AIApplication) -> AIApplication: ...


class EvaluationDatasetRepository(Protocol):
    """Persistence port required by dataset-management use cases."""

    async def add(self, dataset: EvaluationDataset) -> EvaluationDataset: ...

    async def get(self, dataset_id: uuid.UUID) -> EvaluationDataset | None: ...

    async def list(self, *, offset: int, limit: int) -> Sequence[EvaluationDataset]: ...

    async def exists_by_name(self, name: str) -> bool: ...


class RepositoryConflictError(Exception):
    """Raised when a persistence uniqueness invariant is violated."""
