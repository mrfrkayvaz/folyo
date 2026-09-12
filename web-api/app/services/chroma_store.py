"""Chroma sink: doküman ekleme/silme/query — senkron op'lar thread'de, async dış API."""

import threading
import time

import anyio
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..core.config import get_settings
from ..core.logging import get_logger
from . import bm25_index, chroma_codec
from .ai import AIError
from .types import Chunk

LOG = get_logger("chroma")

_client = None
_collection = None
_lock = threading.Lock()


def _space_of(collection) -> str | None:
    """Koleksiyonun vektör uzayı (hnsw.configuration veya metadata'dan)."""
    try:
        cfg = collection.configuration or {}
        space = ((cfg.get("hnsw") or {}).get("space")) or None
        if space:
            return str(space).lower()
    except Exception:
        pass
    return str((collection.metadata or {}).get("hnsw:space", "")).lower() or None


def _col():
    global _client, _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                _client = chromadb.PersistentClient(
                    path=get_settings().chroma_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                _collection = _client.get_or_create_collection(
                    "documents",
                    metadata={"hnsw:space": "cosine"},
                )
                # ÖNEMLİ: `get_or_create` mevcut koleksiyona metadata'yı UYGULAMAZ; eski
                # bir kurulumda uzay 'l2' kalmış olabilir. L2'de `1 − distance` anlamsız/
                # negatif skor üretir ve kosinüs eşiği asla geçilemez → kosinüse çevir.
                space = _space_of(_collection)
                if space != "cosine":
                    LOG.warning(
                        "Chroma koleksiyon uzayı '%s' (cosine değil) → cosine'e çevriliyor; "
                        "belgelerin yeniden embed edilmesi gerekir.",
                        space or "bilinmiyor",
                    )
                    _recreate_collection_locked()
    return _collection


def _recreate_collection_locked() -> None:
    """Koleksiyonu cosine metadata'sıyla yeniden yaratır (kilit ZATEN tutuluyorken)."""
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


def _reset_collection_sync():
    """MANUEL/OPSİYONEL reset: koleksiyonu cosine ile sıfırdan yaratır (kilidi alır).

    Otomatik tek çağrı yeri uzay uyuşmazlığıdır (`_col`); dim uyuşmazlığı koleksiyonu
    ASLA silmez (`_ensure_dim`). Tüm workspace'lerin indeksini siler; yeniden indeksleme gerekir.
    """
    with _lock:
        _recreate_collection_locked()


def _reset_client(why: str) -> None:
    """Chroma istemcisini sıfırlar; bir sonraki erişimde `_col()` taze açar.

    Multi-process kullanımda (web-api + web-worker aynı `chroma.sqlite3` dosyasına
    yazar/okur) uzun ayakta kalan bir süreçteki istemci, diğer sürecin yazmasından
    sonra bayatlayıp hata üretebilir. Hatada istemciyi yeniden açmak sorunu
    restart beklemeden kendi kendine iyileştirir (koleksiyon/veri silinmez).
    """
    global _client, _collection
    with _lock:
        LOG.warning("Chroma istemcisi sıfırlanıyor: %s", why)
        _client = None
        _collection = None


def _run_with_reopen_retry(fn, *args, attempts: int = 3):
    """`fn`'i çalıştırır; Chroma hatasında istemciyi sıfırlayıp yeniden dener.

    Boyut uyuşmazlığı (`AIError`) tanısal hatadır → yeniden denenmez, fırlatılır.
    Geçici kilit ("database is locked") için denemeler arasında kısa bekleme vardır.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn(*args)
        except AIError:
            raise
        except Exception as exc:
            last = exc
            if i + 1 < attempts:
                _reset_client(f"{type(exc).__name__}: {exc} (deneme {i + 1})")
                time.sleep(0.3 * (i + 1))
    assert last is not None
    raise last


def _ensure_dim(collection, dim: int, model: str) -> None:
    """Koleksiyon boyut bekçisi: embed boyutu uyuşmazsa koleksiyonu ASLA silme.

    İlk eklemede dim + model koleksiyon metadata'sına yazılır; sonraki ekleme/sorgularda
    uyuşmazlık açıklayıcı bir hatayla durdurulur (veri kaybı önlenir). Manuel geçiş için
    koleksiyonun bilinçli olarak yeniden indekslenmesi gerekir.
    """
    meta = dict(collection.metadata or {})
    existing = meta.get("embed_dim")
    if existing is not None and int(existing) != int(dim):
        raise AIError(
            f"Embed boyutu koleksiyonla uyuşmuyor: koleksiyon {existing} boyutunda, "
            f"model {dim} boyut üretiyor ({model}). Koleksiyon reset edilmedi — veri kaybını "
            "önlemek için önce indeksler yeniden oluşturulmalı."
        )
    if existing is None:
        meta.setdefault("hnsw:space", "cosine")
        meta["embed_dim"] = int(dim)
        meta["embed_model"] = model
        try:
            collection.modify(metadata=meta)
        except Exception:
            pass  # metadata güncellenemezse boyut bekçisi sonraki eklemelerde yine çalışır


def _upsert_sync(
    workspace_id: str,
    document_id: str,
    name: str,
    ids: list[str],
    documents: list[str],
    metas: list[dict],
    vectors,
) -> None:
    """Idempotent batch yazma (Chroma `upsert`): aynı id üzerine tekrar yazılabilir.
    Vektörler numpy olarak geçilir — `tolist()` kopyası yok, bellek etkisi düşük."""
    _run_with_reopen_retry(
        _upsert_sync_inner, workspace_id, document_id, name, ids, documents, metas, vectors
    )


def _upsert_sync_inner(
    workspace_id: str,
    document_id: str,
    name: str,
    ids: list[str],
    documents: list[str],
    metas: list[dict],
    vectors,
) -> None:
    col = _col()
    dim = int(vectors.shape[1]) if hasattr(vectors, "shape") else len(vectors[0])
    _ensure_dim(col, dim, get_settings().embed_model or "?")
    col.upsert(ids=ids, documents=documents, embeddings=vectors, metadatas=metas)


async def upsert_chunks(
    workspace_id: str,
    document_id: str,
    name: str,
    ids: list[str],
    documents: list[str],
    metas: list[dict],
    vectors,
) -> None:
    """Bir chunk batch'ini Chroma'ya yazar (idempotent — akışlı yazma için)."""
    await anyio.to_thread.run_sync(
        _upsert_sync, workspace_id, document_id, name, ids, documents, metas, vectors
    )


def _delete_doc_sync(document_id: str) -> None:
    def run():
        try:
            res = _col().get(where={"document_id": document_id}, include=["metadatas"])
            metas = res.get("metadatas") or []
            ws_id = (metas[0] or {}).get("workspace_id") if metas else None
        except Exception:
            ws_id = None
        _col().delete(where={"document_id": document_id})
        return ws_id

    ws_id = _run_with_reopen_retry(run)
    if ws_id:
        bm25_index.invalidate(ws_id)


def _delete_ws_sync(workspace_id: str) -> None:
    _run_with_reopen_retry(lambda: _col().delete(where={"workspace_id": workspace_id}))
    bm25_index.invalidate(workspace_id)
    bm25_index.clear_workspace(workspace_id)


def _query_sync(workspace_id: str, vec, top_k: int) -> list[dict]:
    return _run_with_reopen_retry(_query_sync_inner, workspace_id, vec, top_k)


def _query_sync_inner(workspace_id: str, vec, top_k: int) -> list[dict]:
    try:
        res = _col().query(
            query_embeddings=[vec.tolist()],
            n_results=top_k,
            where={"workspace_id": workspace_id},
        )
    except Exception as exc:
        if "dimension" in str(exc).lower():
            raise AIError(
                f"Embed boyutu koleksiyonla uyuşmuyor ({exc}) — sorgu yapılamıyor. "
                "Koleksiyon yeniden indekslenmelidir."
            ) from exc
        raise

    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    return [
        chroma_codec.parse_query_row(metas[i] or {}, docs[i] or "", dists[i] if i < len(dists) else None)
        for i in range(len(ids))
    ]


def _get_ws_sync(workspace_id: str) -> list[dict]:
    def run() -> list[dict]:
        res = _col().get(where={"workspace_id": workspace_id}, include=["documents", "metadatas"])
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        return [
            chroma_codec.parse_get_row(metas[i] or {}, docs[i] or "")
            for i in range(len(docs))
        ]

    return _run_with_reopen_retry(run)


async def add(workspace_id, document_id, name, chunks: list[Chunk], vectors) -> None:
    await anyio.to_thread.run_sync(
        _add_sync, str(workspace_id), str(document_id), name, chunks, vectors
    )


async def delete_document(document_id) -> None:
    await anyio.to_thread.run_sync(_delete_doc_sync, str(document_id))


async def delete_workspace(workspace_id) -> None:
    await anyio.to_thread.run_sync(_delete_ws_sync, str(workspace_id))


def _get_doc_sync(document_id: str) -> list[dict]:
    """Bir belgenin tüm chunk'larını (chunk_index sıralı) döndürür — zenginleştirme için."""
    def run() -> list[dict]:
        res = _col().get(where={"document_id": document_id}, include=["documents", "metadatas"])
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        rows = [chroma_codec.parse_get_row(metas[i] or {}, docs[i] or "") for i in range(len(docs))]
        rows.sort(key=lambda r: r["chunk_index"])
        return rows

    return _run_with_reopen_retry(run)


async def get_chunks_by_document(document_id) -> list[dict]:
    """Belge chunk'larını Chroma'dan çeker (worker zenginleştirme görevi için)."""
    return await anyio.to_thread.run_sync(_get_doc_sync, str(document_id))


def _get_ids_sync(ids: list[str]) -> list[dict]:
    """Verilen `doc_id:chunk_index` kimlikleriyle chunk içeriklerini döndürür."""
    if not ids:
        return []
    def run() -> list[dict]:
        res = _col().get(ids=ids, include=["documents", "metadatas"])
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        return [
            chroma_codec.parse_get_row(metas[i] or {}, docs[i] or "")
            for i in range(len(docs))
        ]

    return _run_with_reopen_retry(run)


async def get_chunks_by_ids(ids: list[str]) -> list[dict]:
    """Chunk içeriklerini kimlik listesiyle çeker (InspectModal için)."""
    return await anyio.to_thread.run_sync(_get_ids_sync, list(ids))


async def get_workspace_chunks(workspace_id) -> list[dict]:
    return await anyio.to_thread.run_sync(_get_ws_sync, str(workspace_id))


async def query(workspace_id, vec, top_k: int) -> list[dict]:
    return await anyio.to_thread.run_sync(_query_sync, str(workspace_id), vec, top_k)