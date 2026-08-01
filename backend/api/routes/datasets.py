import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from api.dependencies import EvaluationDatasetServiceDependency
from schemas.datasets import CreateEvaluationDatasetRequest, EvaluationDatasetResponse
from services.datasets import (
    CreateEvaluationDatasetCommand,
    DatasetItemInput,
    ListEvaluationDatasetsQuery,
)

router = APIRouter()


@router.post("", response_model=EvaluationDatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluation_dataset(
    request: CreateEvaluationDatasetRequest,
    service: EvaluationDatasetServiceDependency,
) -> EvaluationDatasetResponse:
    command = CreateEvaluationDatasetCommand(
        name=request.name,
        description=request.description,
        items=tuple(
            DatasetItemInput(
                input_text=item.input_text,
                expected_output=item.expected_output,
                expected_keywords=tuple(item.expected_keywords),
                metadata=item.metadata,
            )
            for item in request.items
        ),
    )
    dataset = await service.create(command)
    return EvaluationDatasetResponse.model_validate(dataset)


@router.get("/{dataset_id}", response_model=EvaluationDatasetResponse)
async def get_evaluation_dataset(
    dataset_id: uuid.UUID,
    service: EvaluationDatasetServiceDependency,
) -> EvaluationDatasetResponse:
    dataset = await service.get(dataset_id)
    return EvaluationDatasetResponse.model_validate(dataset)


@router.get("", response_model=list[EvaluationDatasetResponse])
async def list_evaluation_datasets(
    service: EvaluationDatasetServiceDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[EvaluationDatasetResponse]:
    datasets = await service.list(ListEvaluationDatasetsQuery(offset=offset, limit=limit))
    return [EvaluationDatasetResponse.model_validate(dataset) for dataset in datasets]
