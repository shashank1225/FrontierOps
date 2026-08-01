import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from models.dataset import EvaluationDataset, EvaluationDatasetItem
from repositories.contracts import EvaluationDatasetRepository, RepositoryConflictError
from services.exceptions import (
    EvaluationDatasetAlreadyExistsError,
    EvaluationDatasetNotFoundError,
)


@dataclass(frozen=True, slots=True)
class DatasetItemInput:
    input_text: str
    expected_output: str | None
    expected_keywords: tuple[str, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CreateEvaluationDatasetCommand:
    name: str
    description: str | None
    items: tuple[DatasetItemInput, ...]


@dataclass(frozen=True, slots=True)
class ListEvaluationDatasetsQuery:
    offset: int = 0
    limit: int = 50


class EvaluationDatasetService:
    """Evaluation dataset use cases independent of transport and persistence frameworks."""

    def __init__(self, repository: EvaluationDatasetRepository) -> None:
        self._repository = repository

    async def create(self, command: CreateEvaluationDatasetCommand) -> EvaluationDataset:
        if await self._repository.exists_by_name(command.name):
            raise EvaluationDatasetAlreadyExistsError(command.name)

        dataset = EvaluationDataset(name=command.name, description=command.description)
        dataset.items.extend(
            EvaluationDatasetItem(
                input_text=item.input_text,
                expected_output=item.expected_output,
                expected_keywords=list(item.expected_keywords),
                metadata_=item.metadata,
            )
            for item in command.items
        )
        try:
            return await self._repository.add(dataset)
        except RepositoryConflictError as error:
            raise EvaluationDatasetAlreadyExistsError(command.name) from error

    async def get(self, dataset_id: uuid.UUID) -> EvaluationDataset:
        dataset = await self._repository.get(dataset_id)
        if dataset is None:
            raise EvaluationDatasetNotFoundError(dataset_id)
        return dataset

    async def list(self, query: ListEvaluationDatasetsQuery) -> Sequence[EvaluationDataset]:
        return await self._repository.list(offset=query.offset, limit=query.limit)
