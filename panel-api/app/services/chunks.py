import json

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..core.config import get_settings
from shared.core.constants import COLLECTION_NAME

_client = None


def _collection():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=get_settings().chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client.get_or_create_collection(COLLECTION_NAME)


def _json_list(raw, default: list):
    if not raw:
        return default
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else default
    except json.JSONDecodeError:
        return default


def chunks_for(document_id: str) -> list[dict]:
    res = _collection().get(where={"document_id": document_id}, include=["documents", "metadatas"])
    out = []
    for meta, text in zip(res.get("metadatas") or [], res.get("documents") or []):
        out.append(
            {
                "chunk_index": int(meta.get("chunk_index", 0)),
                "content_type": meta.get("content_type", "text"),
                "page_number": int(meta.get("page_number", 0)),
                "breadcrumbs": _json_list(meta.get("breadcrumbs"), []),
                "section_title": meta.get("section_title", ""),
                "image_path": meta.get("image_path", ""),
                "image_kind": meta.get("image_kind", ""),
                "bbox": _json_list(meta.get("bbox"), []),
                "text": text or "",
            }
        )
    out.sort(key=lambda c: c["chunk_index"])
    return out