"""Belge yükleme: doğrula → DB kaydı → storage'a akış → ARQ kuyruğuna bırak."""

import urllib.parse
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from shared.core import fs as core_fs
from shared.core.constants import MAX_UPLOAD_SIZE
from ...core.database import get_factory
from ...core.security import require_auth
from shared.core.enums import DocumentStatus
from shared.core.logging import get_logger
from shared.core.taskq import enqueue as taskq_enqueue
from shared.models import Document, EmbeddingJob, Workspace
from ...services import upload
from shared.services.extract.constants import SUPPORTED_EXTS
from ...services.jobs import storage_dir

router = APIRouter(dependencies=[Depends(require_auth)])
LOG = get_logger("api.documents.upload")


@router.post("/workspaces/{wid}/documents")
async def upload_document(wid: uuid.UUID, request: Request):
    filename = urllib.parse.unquote(request.headers.get("X-Filename", "belge"))
    filename = Path(filename).name
    try:
        size = int(request.query_params.get("size") or 0)
    except ValueError:
        size = 0

    # Ön-doğrulama: gövde akışı BAŞLAMADAN önce uzantı ve boyut kontrolü.
    file_ext = Path(filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTS:
        allowed = ", ".join(sorted(SUPPORTED_EXTS))
        raise HTTPException(
            415,
            detail=f"Desteklenmeyen dosya türü '{file_ext or '(uzantı yok)'}'. "
            f"Desteklenen dosyalar: {allowed}.",
        )
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Dosya çok büyük (limit: 25 MB).")

    file_type = file_ext.lstrip(".")

    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")
        doc = Document(workspace_id=wid, filename=filename, file_type=file_type, size=size)
        s.add(doc)
        await s.commit()
        await s.refresh(doc)

    ddir = storage_dir(doc.id)
    ddir.mkdir(parents=True, exist_ok=True)
    path = ddir / filename
    result = await upload.stream_to_disk(request, path, size)

    if result.aborted or result.incomplete:
        async with get_factory()() as s:
            d = await s.get(Document, doc.id)
            if d:
                d.status = DocumentStatus.cancelled
                d.updated_at = d.updated_at.__class__.now()
                s.add(d)
                await s.commit()
        await core_fs.rmtree_ignore(ddir)
        return {"id": str(doc.id), "filename": filename, "status": "cancelled"}

    async with get_factory()() as s:
        d = await s.get(Document, doc.id)
        if d:
            d.status = DocumentStatus.pending
            d.updated_at = d.updated_at.__class__.now()
            s.add(d)
            job = EmbeddingJob(id=doc.id, document_id=doc.id)
            s.add(job)
            await s.commit()

    # Embed görevini ARQ kuyruğuna bırak (ayrı worker süreci tüketir).
    try:
        await taskq_enqueue("embed_document", str(wid), str(doc.id), filename)
    except Exception as exc:
        LOG.error(
            "[upload] belge %s embed görevi kuyruğa atılamadı: %s — "
            "belge pending'de kalacak; redis/worker gelince recover yeniden zamanlayacak.",
            doc.id,
            exc,
        )
    return {"id": str(doc.id), "filename": filename, "status": "pending"}