"""Workspace-geneli BM25 indeksi — lazy kurulum + cache (rag_arch §3B).

İlk sorguda o çalışma alanının TÜM chunk metinleri Chroma'dan çekilir ve
`BM25Okapi` kurulur; workspace bazında cache'lenir. Belge ekleme/silme
`chroma_store` tarafından `invalidate()` çağrısıyla cache'i düşürür.

Neden tüm workspace? Aday-kümesi BM25'i, sparse recall'ı dense recall'a
hapseder; birebir eşleşme (fatura no / TC no) ancak bağımsız bir sparse
kanalla yakalanır.
"""

import threading

from . import bm25

# ws_id -> {"index": BM25Okapi | None, "chunks": list[dict]}
_cache: dict[str, dict] = {}
_lock = threading.Lock()


def invalidate(workspace_id) -> None:
    """Workspace'in indeks cache'ini düşürür (belge ekleme/silme sonrası)."""
    with _lock:
        _cache.pop(str(workspace_id), None)


async def get_index(workspace_id) -> tuple:
    """`(BM25Okapi | None, chunks)` döndürür; gerekirse Chroma'dan kurar."""
    from . import chroma_store  # döngüsel import'u önlemek için lazy

    ws_id = str(workspace_id)
    with _lock:
        cached = _cache.get(ws_id)
    if cached is not None:
        return cached["index"], cached["chunks"]

    chunks = await chroma_store.get_workspace_chunks(ws_id)
    corpus = [c["text"] for c in chunks]
    index = bm25.BM25Okapi(corpus) if corpus else None
    with _lock:
        _cache[ws_id] = {"index": index, "chunks": chunks}
    return index, chunks