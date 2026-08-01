from typing import cast
from unittest.mock import AsyncMock

import pytest

from repositories.contracts import EvaluationDatasetRepository, RepositoryConflictError
from services.datasets import (
    CreateEvaluationDatasetCommand,
    DatasetItemInput,
    EvaluationDatasetService,
)
from services.exceptions import EvaluationDatasetAlreadyExistsError


def make_command() -> CreateEvaluationDatasetCommand:
    return CreateEvaluationDatasetCommand(
        name="Support Golden Set",
        description="Curated support cases",
        items=(
            DatasetItemInput(
                input_text="What is the refund period?",
                expected_output="30 days",
                expected_keywords=("refund", "30 days"),
                metadata={"category": "policy"},
            ),
        ),
    )


async def test_create_builds_dataset_aggregate() -> None:
    repository = AsyncMock()
    repository.exists_by_name.return_value = False
    repository.add.side_effect = lambda dataset: dataset
    service = EvaluationDatasetService(cast(EvaluationDatasetRepository, repository))

    dataset = await service.create(make_command())

    assert dataset.name == "Support Golden Set"
    assert len(dataset.items) == 1
    assert dataset.items[0].expected_keywords == ["refund", "30 days"]
    assert dataset.items[0].metadata_ == {"category": "policy"}
    repository.add.assert_awaited_once_with(dataset)


async def test_create_rejects_duplicate_name() -> None:
    repository = AsyncMock()
    repository.exists_by_name.return_value = True
    service = EvaluationDatasetService(cast(EvaluationDatasetRepository, repository))

    with pytest.raises(EvaluationDatasetAlreadyExistsError):
        await service.create(make_command())


async def test_create_translates_database_uniqueness_race() -> None:
    repository = AsyncMock()
    repository.exists_by_name.return_value = False
    repository.add.side_effect = RepositoryConflictError
    service = EvaluationDatasetService(cast(EvaluationDatasetRepository, repository))

    with pytest.raises(EvaluationDatasetAlreadyExistsError):
        await service.create(make_command())
