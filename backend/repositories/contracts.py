import uuid
from collections.abc import Sequence
from typing import Protocol

from evaluation.history import EvaluationRunFilter
from models.application import AIApplication
from models.dataset import EvaluationDataset
from models.evaluation import EvaluationResult, EvaluationRun
from models.prompt import PromptVersion


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


class EvaluationRunRepository(Protocol):
    """Persistence port for evaluation run lifecycle and case results."""

    async def add(self, run: EvaluationRun) -> EvaluationRun: ...

    async def save(self, run: EvaluationRun) -> EvaluationRun: ...

    async def add_result(self, result: EvaluationResult) -> EvaluationResult: ...

    async def get(self, run_id: uuid.UUID) -> EvaluationRun | None: ...

    async def list_filtered(
        self, filters: EvaluationRunFilter
    ) -> tuple[Sequence[EvaluationRun], int]: ...

    async def get_latest_completed(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> EvaluationRun | None: ...


class PromptVersionRepository(Protocol):
    async def create_next(
        self,
        application_id: uuid.UUID,
        template: str,
        change_summary: str | None,
    ) -> PromptVersion | None: ...

    async def get_for_application(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> PromptVersion | None: ...

    async def list_for_application(self, application_id: uuid.UUID) -> Sequence[PromptVersion]: ...

    async def activate(
        self, application_id: uuid.UUID, prompt_version_id: uuid.UUID
    ) -> PromptVersion | None: ...


class RepositoryConflictError(Exception):
    """Raised when a persistence uniqueness invariant is violated."""
