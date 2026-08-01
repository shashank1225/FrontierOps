from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from services.exceptions import (
    ApplicationAlreadyExistsError,
    ApplicationNotFoundError,
    EvaluationDatasetAlreadyExistsError,
    EvaluationDatasetNotFoundError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Translate use-case errors at the outer HTTP boundary."""

    @app.exception_handler(ApplicationAlreadyExistsError)
    async def application_conflict(
        _request: Request, error: ApplicationAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(error), "code": "application_already_exists"},
        )

    @app.exception_handler(ApplicationNotFoundError)
    async def application_not_found(
        _request: Request, error: ApplicationNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(error), "code": "application_not_found"},
        )

    @app.exception_handler(EvaluationDatasetNotFoundError)
    async def dataset_not_found(
        _request: Request, error: EvaluationDatasetNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(error), "code": "evaluation_dataset_not_found"},
        )

    @app.exception_handler(EvaluationDatasetAlreadyExistsError)
    async def dataset_conflict(
        _request: Request, error: EvaluationDatasetAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(error), "code": "evaluation_dataset_already_exists"},
        )
