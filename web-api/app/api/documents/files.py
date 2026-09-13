"""Belge dosyaları: orijinal + kırpım görselleri servis eder (depolama)."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...core.database import get_factory
from shared.models import Document
from ...services.jobs import storage_dir

router = APIRouter()


@router.get("/documents/{did}/file")
async def download_document(did: uuid.UUID):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
    p = storage_dir(did) / d.filename
    if not p.exists():
        raise HTTPException(404, "Dosya depoda yok.")
    return FileResponse(p, filename=d.filename)


@router.get("/documents/{did}/crops/{name}")
async def get_crop(did: uuid.UUID, name: str):
    async with get_factory()() as s:
        d = await s.get(Document, did)
        if not d:
            raise HTTPException(404, "Belge bulunamadı.")
    p = storage_dir(did) / "crops" / Path(name).name
    if not p.exists():
        raise HTTPException(404, "Kırpım bulunamadı.")
    return FileResponse(p)