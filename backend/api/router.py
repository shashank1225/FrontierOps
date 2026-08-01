from fastapi import APIRouter

from api.routes.applications import router as applications_router
from api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(applications_router, prefix="/applications", tags=["applications"])
