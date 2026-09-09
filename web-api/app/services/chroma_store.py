import anyio
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..core.config import get_settings

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


def _reset_collection_sync():
    global _client, _collection
    if _client is not None:
        try:
            _client.delete_collection("documents")
        except Exception:
            pass
        _collection = _client.get_or_create_collection(
            "documents",
            metadata={"hnsw:space": "cosine"},
        )


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
    try:
        _col().add(ids=ids, documents=chunks, embeddings=vectors.tolist(), metadatas=metas)
    except Exception as e:
        if "dimension" in str(e).lower():
            _reset_collection_sync()
            _col().add(ids=ids, documents=chunks, embeddings=vectors.tolist(), metadatas=metas)
        else:
            raise e


def _delete_doc_sync(document_id: str) -> None:
    _col().delete(where={"document_id": document_id})


def _delete_ws_sync(workspace_id: str) -> None:
    _col().delete(where={"workspace_id": workspace_id})


def _query_sync(workspace_id: str, vec, top_k: int) -> list[dict]:
    try:
        res = _col().query(
            query_embeddings=[vec.tolist()],
            n_results=top_k,
            where={"workspace_id": workspace_id},
        )
    except Exception as e:
        if "dimension" in str(e).lower():
            _reset_collection_sync()
            return []
        raise e

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


async def add(workspace_id, document_id, name, chunks, vectors) -> None:
    await anyio.to_thread.run_sync(_add_sync, str(workspace_id), str(document_id), name, chunks, vectors)


async def delete_document(document_id) -> None:
    await anyio.to_thread.run_sync(_delete_doc_sync, str(document_id))


async def delete_workspace(workspace_id) -> None:
    await anyio.to_thread.run_sync(_delete_ws_sync, str(workspace_id))


async def query(workspace_id, vec, top_k: int) -> list[dict]:
    return await anyio.to_thread.run_sync(_query_sync, str(workspace_id), vec, top_k)