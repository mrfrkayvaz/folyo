"""ARQ iş gövdeleleri — Redis kuyruğundan gelen görevler için ince sarmalayıcılar.

Görev adları (`embed_document`, `enrich_document`, `workspace_summary`)
`worker_settings.py` ve `core/taskq.enqueue` çağrılarıyla birebir eşleşir.
"""

import uuid

from .services.jobs.embed import run_embed_job as _embed
from .services.jobs.enrich import do_workspace_summary as _workspace_summary
from .services.jobs.enrich import enrich_document as _enrich_document


async def embed_document(ctx, workspace_id: str, document_id: str, filename: str) -> str:
    """Belgeyi embed et (extract → chunk → vektör → chroma)."""
    await _embed(uuid.UUID(workspace_id), uuid.UUID(document_id), filename)
    return "ok"


async def enrich_document(ctx, workspace_id: str, document_id: str) -> str:
    """Belge özeti + starter sorular (chunk'ları Chroma'dan okur)."""
    await _enrich_document(uuid.UUID(workspace_id), uuid.UUID(document_id))
    return "ok"


async def workspace_summary(ctx, workspace_id: str) -> str:
    """Workspace özeti + başlık (belge özetlerinin sentezi)."""
    await _workspace_summary(uuid.UUID(workspace_id))
    return "ok"