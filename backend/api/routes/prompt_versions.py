import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from api.dependencies import PromptVersionServiceDependency
from schemas.prompt_versions import (
    CreatePromptVersionRequest,
    PromptVersionComparisonResponse,
    PromptVersionResponse,
)

router = APIRouter()


@router.post(
    "/{application_id}/prompt-versions",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    application_id: uuid.UUID,
    request: CreatePromptVersionRequest,
    service: PromptVersionServiceDependency,
) -> PromptVersionResponse:
    prompt = await service.create(application_id, request.template, request.change_summary)
    return PromptVersionResponse.model_validate(prompt)


@router.get("/{application_id}/prompt-versions", response_model=list[PromptVersionResponse])
async def list_prompt_versions(
    application_id: uuid.UUID, service: PromptVersionServiceDependency
) -> list[PromptVersionResponse]:
    prompts = await service.list(application_id)
    return [PromptVersionResponse.model_validate(prompt) for prompt in prompts]


@router.put(
    "/{application_id}/prompt-versions/{prompt_version_id}/activate",
    response_model=PromptVersionResponse,
)
async def activate_prompt_version(
    application_id: uuid.UUID,
    prompt_version_id: uuid.UUID,
    service: PromptVersionServiceDependency,
) -> PromptVersionResponse:
    prompt = await service.activate(application_id, prompt_version_id)
    return PromptVersionResponse.model_validate(prompt)


@router.get(
    "/{application_id}/prompt-versions/compare",
    response_model=PromptVersionComparisonResponse,
)
async def compare_prompt_versions(
    application_id: uuid.UUID,
    service: PromptVersionServiceDependency,
    baseline_version_id: Annotated[uuid.UUID, Query()],
    candidate_version_id: Annotated[uuid.UUID, Query()],
) -> PromptVersionComparisonResponse:
    comparison = await service.compare(application_id, baseline_version_id, candidate_version_id)
    return PromptVersionComparisonResponse.model_validate(comparison)
