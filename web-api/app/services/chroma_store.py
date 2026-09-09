"""ChromaDB vektör deposu (API içinde, kalıcı dizin).

Vektörleri biz üretiriz (OpenRouter embedding) — chroma'nın kendi modelini indirmeyiz.
Tüm kayıtlarda workspace_id metadata'sı vardır → sorgular her zaman workspace-scope'lu.
Bloke eden çağrılar anyio.to_thread ile event-loop'u kilitlemez.
"""

import anyio
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import get_settings

_client = None
_collection = None


def _col():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=get_settings().chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            "documents",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _add_sync(workspace_id: str, document_id: str, name: str, chunks: list[str], vectors) -> None:
    ids = [f"{document_id}:{i}" for i in range(len(chunks))]
    metas = [
        {
            "workspace_id": workspace_id,
            "document_id": document_id,
            "doc_index": i,
            "name": name,
        }
        for i in range(len(chunks))
    ]
    _col().add(ids=ids, documents=chunks, embeddings=vectors.tolist(), metadatas=metas)


def _delete_doc_sync(document_id: str) -> None:
    _col().delete(where={"document_id": document_id})


def _delete_ws_sync(workspace_id: str) -> None:
    _col().delete(where={"workspace_id": workspace_id})


def _query_sync(workspace_id: str, vec, top_k: int) -> list[dict]:
    res = _col().query(
        query_embeddings=[vec.tolist()],
        n_results=top_k,
        where={"workspace_id": workspace_id},
    )
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out = []
    for i in range(len(ids)):
        meta = metas[i] or {}
        out.append(
            {
                "doc_id": meta.get("document_id", ""),
                "doc_index": int(meta.get("doc_index", 0)),
                "name": meta.get("name", "?"),
                "text": docs[i] or "",
                "score": round(1.0 - float(dists[i]), 4) if dists else 0.0,
            }
        )
    return out


# ── async sarmalayıcılar ──────────────────────────────────────────────────────


async def add(workspace_id, document_id, name, chunks, vectors) -> None:
    await anyio.to_thread.run_sync(_add_sync, str(workspace_id), str(document_id), name, chunks, vectors)


async def delete_document(document_id) -> None:
    await anyio.to_thread.run_sync(_delete_doc_sync, str(document_id))


async def delete_workspace(workspace_id) -> None:
    await anyio.to_thread.run_sync(_delete_ws_sync, str(workspace_id))


async def query(workspace_id, vec, top_k: int) -> list[dict]:
    return await anyio.to_thread.run_sync(_query_sync, str(workspace_id), vec, top_k)