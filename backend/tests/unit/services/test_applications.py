import uuid
from typing import cast
from unittest.mock import AsyncMock

import pytest

from models.enums import DeploymentStatus
from repositories.contracts import ApplicationRepository, RepositoryConflictError
from services.applications import ApplicationService, RegisterApplicationCommand
from services.exceptions import (
    ApplicationAlreadyExistsError,
    EvaluationDatasetNotFoundError,
)


def make_command(**overrides: object) -> RegisterApplicationCommand:
    values: dict[str, object] = {
        "name": "Support Copilot",
        "description": "Answers support questions",
        "provider": "ollama",
        "model": "llama3.2",
        "prompt_template": "Answer: {input}",
        "prompt_change_summary": "Initial prompt",
        "evaluation_dataset_id": None,
    }
    values.update(overrides)
    return RegisterApplicationCommand(**values)  # type: ignore[arg-type]


async def test_register_builds_complete_draft_aggregate() -> None:
    repository = AsyncMock()
    repository.exists_by_name.return_value = False
    repository.add.side_effect = lambda application: application
    service = ApplicationService(cast(ApplicationRepository, repository))

    application = await service.register(make_command())

    assert application.deployment_status is DeploymentStatus.DRAFT
    assert application.prompt_versions[0].version == 1
    assert application.prompt_versions[0].is_active is True
    assert application.active_prompt_version is application.prompt_versions[0]
    assert application.release_gate_policy is not None
    assert application.release_gate_policy.minimum_quality_score == 0.75
    repository.add.assert_awaited_once_with(application)


async def test_register_rejects_duplicate_name() -> None:
    repository = AsyncMock()
    repository.exists_by_name.return_value = True
    service = ApplicationService(cast(ApplicationRepository, repository))

    with pytest.raises(ApplicationAlreadyExistsError):
        await service.register(make_command())

    repository.add.assert_not_awaited()


async def test_register_rejects_unknown_dataset() -> None:
    dataset_id = uuid.uuid4()
    repository = AsyncMock()
    repository.exists_by_name.return_value = False
    repository.dataset_exists.return_value = False
    service = ApplicationService(cast(ApplicationRepository, repository))

    with pytest.raises(EvaluationDatasetNotFoundError):
        await service.register(make_command(evaluation_dataset_id=dataset_id))


async def test_register_translates_database_uniqueness_race() -> None:
    repository = AsyncMock()
    repository.exists_by_name.return_value = False
    repository.add.side_effect = RepositoryConflictError
    service = ApplicationService(cast(ApplicationRepository, repository))

    with pytest.raises(ApplicationAlreadyExistsError):
        await service.register(make_command())
