"""Workspace-geneli BM25 indeksi — lazy kurulum + stale-serve'li arka plan rebuild.

İlk sorguda o çalışma alanının TÜM chunk metinleri Chroma'dan çekilir ve
`BM25Okapi` kurulur; workspace bazında cache'lenir.

Ölçek davranışı (rag_arch §3B / C3):
- `invalidate()` cache'i düşürmez; `dirty` bayrağı + revizyon sayacı kurar.
- `get_index()` bayat indeksi **döndürmeye devam eder** (stale-serve) ve rebuild'i
  arka planda tetikler → API istekleri hiçbir zaman BM25 kurulumunda bloklanmaz.
- Kurulum (CPU ağır iş) `anyio.to_thread` ile iş parçacığına alınır; event loop serbest kalır.
- Build sırasında yeni invalidate gelirse revizyon kontrolü bayrağı yeniden kurar
  (konverjans: bir sonraki sorguda bir rebuild daha), cache asla yanlış "temiz" kalmaz.
- Soğuk başlangıçta (cache yokken) build beklenir — ama thread'de kurulduğu için
  event loop diğer isteklerle çalışmaya devam eder; hata durumunda hata yeniden fırlatılır.

Neden tüm workspace? Aday-kümesi BM25'i, sparse recall'ı dense recall'a
hapseder; birebir eşleşme (fatura no / TC no) ancak bağımsız bir sparse
kanalla yakalanır.
"""

import asyncio
import threading

import anyio

from ..core.config import get_settings
from . import bm25

# ws_id -> {"index": BM25Okapi | None, "chunks": list[dict]}
_cache: dict[str, dict] = {}
# ws_id -> bayat işareti (cache var ama eski)
_dirty: set[str] = set()
# ws_id -> revizyon sayacı (her invalidate +1; build sırasında değişirse tekrar bayatla)
_rev: dict[str, int] = {}
# ws_id -> in-flight rebuild task'leri (per-ws tek build garantisi)
_build_tasks: dict[str, asyncio.Task] = {}
# ws_id -> son build hatası (soğuk başlangıçta yeniden fırlatılır)
_errors: dict[str, BaseException] = {}
_lock = threading.Lock()


def invalidate(workspace_id) -> None:
    """Belge ekleme/silme sonrası: indeksi bayat işaretle (blocking rebuild YOK)."""
    ws_id = str(workspace_id)
    with _lock:
        _dirty.add(ws_id)
        _rev[ws_id] = _rev.get(ws_id, 0) + 1


def _schedule_rebuild(ws_id: str) -> "asyncio.Task":
    """Per-ws tek rebuild task'i garanti eder; bitmemiş task varsa onu döndürür.

    Bitmiş ancak done-callback'i henüz çalışmamış task'lar yeniden kurulur
    (yarış: `await task` ile callback arasında yeni istek gelebilir).
    """
    with _lock:
        task = _build_tasks.get(ws_id)
        if task is not None and not task.done():
            return task
        task = asyncio.create_task(_rebuild(ws_id))
        _build_tasks[ws_id] = task

    def _done(t) -> None:
        with _lock:
            # Kimlik kontrolü: bir sonraki task'ı yanlışlıkla düşürme.
            if _build_tasks.get(ws_id) is t:
                _build_tasks.pop(ws_id, None)

    task.add_done_callback(_done)
    return task


async def _rebuild(ws_id: str) -> None:
    """Chroma'dan tüm chunk'ları çeker, BM25'i thread'de kurar, cache'i atomik değiştirir."""
    from . import chroma_store  # döngüsel import'u önlemek için lazy

    with _lock:
        rev_start = _rev.get(ws_id, 0)

    try:
        chunks = await chroma_store.get_workspace_chunks(ws_id)

        def _build() -> bm25.BM25Okapi | None:
            corpus = [c["text"] for c in chunks]
            if not corpus:
                return None
            _s = get_settings()
            return bm25.BM25Okapi(
                corpus,
                stem_min=_s.bm25_stem_min,
                stem_cap=_s.bm25_stem_cap,
            )

        index = await anyio.to_thread.run_sync(_build)

        with _lock:
            # Build sırasında yeni invalidate olduysa bayrağı yeniden kur (konverjans).
            if _rev.get(ws_id, 0) != rev_start:
                _dirty.add(ws_id)
            else:
                _dirty.discard(ws_id)
            _errors.pop(ws_id, None)
            _cache[ws_id] = {"index": index, "chunks": chunks}
    except Exception as exc:
        with _lock:
            _errors[ws_id] = exc
        # Bayat cache ve dirty bayrağı korunur → başka sorgu rebuild'i tekrar dener.


async def get_index(workspace_id) -> tuple:
    """`(BM25Okapi | None, chunks)` döndürür; gerektiğinde arka planda yeniler.

    - Cache hâlâ tazeyse doğrudan döner.
    - Cache bayatsa bayat veriyi döndürür, rebuild'i arka planda tetikler (stale-serve).
    - Cache hiç yoksa (soğuk başlangıç) build'i başlatıp await eder; event loop serbest kalır.
    """
    ws_id = str(workspace_id)

    with _lock:
        cached = _cache.get(ws_id)
    if cached is not None:
        with _lock:
            dirty = ws_id in _dirty
        if dirty:
            _schedule_rebuild(ws_id)
        return cached["index"], cached["chunks"]

    task = _schedule_rebuild(ws_id)
    try:
        await asyncio.shield(task)
    except Exception:
        pass

    with _lock:
        cached = _cache.get(ws_id)
        err = _errors.get(ws_id)
    if cached is not None:
        return cached["index"], cached["chunks"]
    if err is not None:
        with _lock:
            _errors.pop(ws_id, None)
        raise err
    return None, []


def clear_workspace(workspace_id) -> None:
    """Workspace silinirken çağrılabilir: cache/durum alanlarını boşaltır (opsiyonel)."""
    ws_id = str(workspace_id)
    with _lock:
        _cache.pop(ws_id, None)
        _dirty.discard(ws_id)
        _rev.pop(ws_id, None)
        _errors.pop(ws_id, None)
        task = _build_tasks.pop(ws_id, None)
    if task is not None:
        task.cancel()