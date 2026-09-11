"""Chroma metadata kodlama/çözme — JSON alanları ve satır → dict eşlemesi."""

import json

from .types import Chunk


def chunk_metadata(workspace_id: str, document_id: str, name: str, c: Chunk) -> dict:
    return {
        "workspace_id": workspace_id,
        "document_id": document_id,
        "name": name,
        "page_number": int(c.page_number),
        "chunk_index": int(c.chunk_index),
        "content_type": c.content_type,
        "page_context": c.page_context,
        "breadcrumbs": json.dumps(c.breadcrumbs),
        "section_title": c.breadcrumbs[-1] if c.breadcrumbs else "",
        "image_path": c.image_path,
        "image_kind": c.image_kind,
        "bbox": json.dumps(c.bbox),
    }


def parse_query_row(meta: dict, text: str, distance: float | None) -> dict:
    return {
        "doc_id": meta.get("document_id", ""),
        "chunk_index": int(meta.get("chunk_index", 0)),
        "page_number": int(meta.get("page_number", 1)),
        "content_type": meta.get("content_type", "text"),
        "page_context": meta.get("page_context", ""),
        "breadcrumbs": _json_list(meta.get("breadcrumbs"), []),
        "section_title": meta.get("section_title", ""),
        "image_path": meta.get("image_path", ""),
        "image_kind": meta.get("image_kind", ""),
        "bbox": _json_list(meta.get("bbox"), []),
        "name": meta.get("name", "?"),
        "text": text or "",
        "score": round(1.0 - float(distance), 4) if distance else 0.0,
    }


def parse_get_row(meta: dict, text: str) -> dict:
    return {
        "doc_id": meta.get("document_id", ""),
        "chunk_index": int(meta.get("chunk_index", 0)),
        "page_number": int(meta.get("page_number", 1)),
        "content_type": meta.get("content_type", "text"),
        "image_path": meta.get("image_path", ""),
        "name": meta.get("name", "?"),
        "text": text or "",
    }


def _json_list(raw, default: list):
    if not raw:
        return default
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else default
    except json.JSONDecodeError:
        return default