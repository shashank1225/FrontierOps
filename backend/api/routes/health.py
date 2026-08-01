from fastapi import APIRouter, Response, status

from api.dependencies import HealthServiceDependency
from schemas.health import HealthResponse, ReadinessResponse

router = APIRouter()


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(
    service: HealthServiceDependency,
    response: Response,
) -> ReadinessResponse:
    result = await service.readiness()
    if result.status == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
