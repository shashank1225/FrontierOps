import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from api.dependencies import ApplicationServiceDependency
from schemas.applications import ApplicationResponse, RegisterApplicationRequest
from schemas.datasets import AttachEvaluationDatasetRequest
from services.applications import (
    AttachEvaluationDatasetCommand,
    ListApplicationsQuery,
    RegisterApplicationCommand,
)

router = APIRouter()


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def register_application(
    request: RegisterApplicationRequest,
    service: ApplicationServiceDependency,
) -> ApplicationResponse:
    application = await service.register(RegisterApplicationCommand(**request.model_dump()))
    return ApplicationResponse.model_validate(application)


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    service: ApplicationServiceDependency,
) -> ApplicationResponse:
    application = await service.get(application_id)
    return ApplicationResponse.model_validate(application)


@router.get("", response_model=list[ApplicationResponse])
async def list_applications(
    service: ApplicationServiceDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ApplicationResponse]:
    applications = await service.list(ListApplicationsQuery(offset=offset, limit=limit))
    return [ApplicationResponse.model_validate(application) for application in applications]


@router.put("/{application_id}/evaluation-dataset", response_model=ApplicationResponse)
async def attach_evaluation_dataset(
    application_id: uuid.UUID,
    request: AttachEvaluationDatasetRequest,
    service: ApplicationServiceDependency,
) -> ApplicationResponse:
    application = await service.attach_evaluation_dataset(
        AttachEvaluationDatasetCommand(
            application_id=application_id,
            dataset_id=request.dataset_id,
        )
    )
    return ApplicationResponse.model_validate(application)
