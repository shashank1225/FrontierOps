import uuid
from collections.abc import Sequence

from evaluation.history import EvaluationRunFilter
from models.evaluation import EvaluationRun
from repositories.contracts import EvaluationRunRepository


class EvaluationRunNotFoundError(Exception):
    def __init__(self, run_id: uuid.UUID) -> None:
        super().__init__(f"Evaluation run '{run_id}' was not found.")


class InvalidEvaluationRunFilterError(Exception):
    """Raised when evaluation history filter bounds are inconsistent."""


class EvaluationHistoryService:
    def __init__(self, repository: EvaluationRunRepository) -> None:
        self._repository = repository

    async def get(self, run_id: uuid.UUID) -> EvaluationRun:
        run = await self._repository.get(run_id)
        if run is None:
            raise EvaluationRunNotFoundError(run_id)
        return run

    async def list(self, filters: EvaluationRunFilter) -> tuple[Sequence[EvaluationRun], int]:
        if (
            filters.created_from is not None
            and filters.created_to is not None
            and filters.created_from > filters.created_to
        ):
            raise InvalidEvaluationRunFilterError(
                "created_from must be earlier than or equal to created_to."
            )
        return await self._repository.list_filtered(filters)
