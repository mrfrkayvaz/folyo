import json
import time
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from shared.core.constants import ERROR_QA_GENERIC_FAILURE
from ..core.database import get_factory
from ..core.security import require_auth
from shared.core.enums import ChatRole
from shared.core.logging import get_logger
from shared.models import ChatMessage, Workspace
from shared.services.qalogs import add_log as qa_log
from ..schemas.chat import QaBody
from ..services.rag import qa_events

router = APIRouter(prefix="/api/workspaces", tags=["qa"], dependencies=[Depends(require_auth)])
LOG = get_logger("api.qa")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream(gen):
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{wid}/qa")
async def ask(wid: uuid.UUID, body: QaBody):
    question = body.question.strip()
    if not question:
        raise HTTPException(422, "Soru boş olamaz.")

    async with get_factory()() as s:
        ws = await s.get(Workspace, wid)
        if not ws:
            raise HTTPException(404, "Workspace bulunamadı.")

        user_msg = ChatMessage(workspace_id=wid, role=ChatRole.user, content=question)
        s.add(user_msg)
        await s.commit()
        await s.refresh(user_msg)

    async def gen():
        sf = get_factory()
        acc = ""
        err = None
        meta = None
        start = time.monotonic()
        try:
            async for ev in qa_events(wid, question, message_id=user_msg.id):
                yield _sse(ev["type"], {k: v for k, v in ev.items() if k != "type"})
                if ev["type"] == "delta":
                    acc += ev["text"]
                elif ev["type"] == "meta":
                    meta = ev
                elif ev["type"] == "error":
                    err = ev.get("message") or err
                    LOG.warning("QA error event (wid=%s): %s", wid, err)

            content = acc if acc else (f"⚠️ {err}" if err else ERROR_QA_GENERIC_FAILURE)
            if not acc and not err:
                # Canlıdaki 'cevap gelmedi' durumu: akış boş bitti, hata event'i yok.
                await qa_log(
                    get_factory, workspace_id=wid, message_id=user_msg.id,
                    level="error", stage="sonuç",
                    message=f"BOŞ CEVAP: pipeline hata üretmeden boş döndü — istemci 'uyarı' mesajı aldı "
                    f"({ERROR_QA_GENERIC_FAILURE})",
                )
            elif err:
                await qa_log(
                    get_factory, workspace_id=wid, message_id=user_msg.id,
                    level="error", stage="sonuç",
                    message=f"Yanıt hata olarak kaydedildi: {err}",
                )
            else:
                dur = time.monotonic() - start
                await qa_log(
                    get_factory, workspace_id=wid, message_id=user_msg.id,
                    stage="sonuç",
                    message=f"Yanıt kaydedildi, süre {dur:.1f}s, uzunluk {len(acc)} karakter",
                )
            citations = None
            if meta:
                citations = {
                    "sources": meta.get("sources") or [],
                    "chunk_ids": meta.get("chunk_ids") or [],
                    "confidence": meta.get("confidence"),
                    "confidence_level": meta.get("confidence_level"),
                    "rejected": bool(meta.get("rejected")),
                    "signals": meta.get("signals"),
                }
            async with sf() as s:
                s.add(
                    ChatMessage(
                        workspace_id=wid,
                        role=ChatRole.assistant,
                        content=content,
                        citations=citations,
                    )
                )
                await s.commit()
        except Exception:
            LOG.exception("QA akışı başarısız (wid=%s, soru=%r)", wid, question)
            try:
                await qa_log(
                    get_factory, workspace_id=wid, message_id=user_msg.id,
                    level="error", stage="akış",
                    message=f"Akışta beklenmeyen hata: {traceback.format_exc(limit=5)}",
                )
            except Exception:
                LOG.exception("[qalogs] akış hatası loglanamadı (wid=%s)", wid)
            try:
                async with sf() as s:
                    s.add(
                        ChatMessage(
                            workspace_id=wid,
                            role=ChatRole.assistant,
                            content=ERROR_QA_GENERIC_FAILURE,
                            citations=None,
                        )
                    )
                    await s.commit()
            except Exception:
                LOG.exception("QA hata mesajı DB'ye yazılamadı (wid=%s)", wid)

    return _stream(gen())
