from fastapi import APIRouter

from .documents import router as documents_router
from .health import router as health_router
from .workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(workspaces_router)
api_router.include_router(documents_router)