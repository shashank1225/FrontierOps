from fastapi import APIRouter

from api.routes.applications import router as applications_router
from api.routes.datasets import router as datasets_router
from api.routes.evaluation_jobs import router as evaluation_jobs_router
from api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(applications_router, prefix="/applications", tags=["applications"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
api_router.include_router(evaluation_jobs_router, tags=["evaluations"])
