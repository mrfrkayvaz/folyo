from fastapi import APIRouter

from .auth import router as auth_router
from .documents import router as documents_router
from .health import router as health_router
from .qa_logs import router as qa_logs_router
from .users import router as users_router
from .workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(workspaces_router)
api_router.include_router(documents_router)
api_router.include_router(qa_logs_router)