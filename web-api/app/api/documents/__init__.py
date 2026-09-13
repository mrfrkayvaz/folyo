"""Belge uçları — modüler paket (upload / yönetim / dosya-kırpım)."""

from fastapi import APIRouter

from .files import router as files_router
from .manage import router as manage_router
from .upload import router as upload_router

router = APIRouter(prefix="/api", tags=["documents"])
router.include_router(upload_router)
router.include_router(manage_router)
router.include_router(files_router)