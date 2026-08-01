import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from models.application import AIApplication
from models.enums import DeploymentStatus
from models.prompt import PromptVersion
from models.release_gate import ReleaseGatePolicy
from repositories.contracts import ApplicationRepository, RepositoryConflictError
from services.exceptions import (
    ApplicationAlreadyExistsError,
    ApplicationNotFoundError,
    EvaluationDatasetNotFoundError,
)


@dataclass(frozen=True, slots=True)
class RegisterApplicationCommand:
    name: str
    description: str | None
    provider: str
    model: str
    prompt_template: str
    prompt_change_summary: str | None
    evaluation_dataset_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class ListApplicationsQuery:
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True, slots=True)
class AttachEvaluationDatasetCommand:
    application_id: uuid.UUID
    dataset_id: uuid.UUID


class ApplicationService:
    """Application-management use cases independent of HTTP and SQLAlchemy."""

    def __init__(self, repository: ApplicationRepository) -> None:
        self._repository = repository

    async def register(self, command: RegisterApplicationCommand) -> AIApplication:
        if await self._repository.exists_by_name(command.name):
            raise ApplicationAlreadyExistsError(command.name)

        if command.evaluation_dataset_id is not None and not await self._repository.dataset_exists(
            command.evaluation_dataset_id
        ):
            raise EvaluationDatasetNotFoundError(command.evaluation_dataset_id)

        application = AIApplication(
            name=command.name,
            description=command.description,
            provider=command.provider,
            model=command.model,
            deployment_status=DeploymentStatus.DRAFT,
            evaluation_dataset_id=command.evaluation_dataset_id,
        )
        initial_prompt = PromptVersion(
            version=1,
            template=command.prompt_template,
            change_summary=command.prompt_change_summary,
            is_active=True,
        )
        application.prompt_versions.append(initial_prompt)
        application.active_prompt_version = initial_prompt
        application.release_gate_policy = ReleaseGatePolicy(
            minimum_quality_score=0.75,
            maximum_latency_ms=5000.0,
            maximum_failure_rate=0.05,
            maximum_cost_usd=None,
        )

        try:
            return await self._repository.add(application)
        except RepositoryConflictError as error:
            # The database constraint closes the race between the pre-check and insert.
            raise ApplicationAlreadyExistsError(command.name) from error

    async def get(self, application_id: uuid.UUID) -> AIApplication:
        application = await self._repository.get(application_id)
        if application is None:
            raise ApplicationNotFoundError(application_id)
        return application

    async def list(self, query: ListApplicationsQuery) -> Sequence[AIApplication]:
        return await self._repository.list(offset=query.offset, limit=query.limit)

    async def attach_evaluation_dataset(
        self, command: AttachEvaluationDatasetCommand
    ) -> AIApplication:
        application = await self._repository.get(command.application_id)
        if application is None:
            raise ApplicationNotFoundError(command.application_id)
        if not await self._repository.dataset_exists(command.dataset_id):
            raise EvaluationDatasetNotFoundError(command.dataset_id)

        application.evaluation_dataset_id = command.dataset_id
        return await self._repository.save(application)
