"""shared.services.bm25_index — workspace-geneli BM25 cache + stale-serve rebuild.

Chroma erişimi `shared.services.chroma_store.get_workspace_chunks` mock'lanır;
gerçek DB/Chroma/Redis yok. `invalidate` → bayat serve → arka plan rebuild akışı
odakta. Async testler `@pytest.mark.anyio` ile asyncio backend'de çalışır.
"""

import asyncio
import threading

import pytest

from shared.services import bm25_index
from shared.services.bm25 import BM25Okapi


@pytest.fixture
def reset_index(monkeypatch):
    """Test arası global durumu temizler (cache/dirty/rev/tasks/errors)."""
    prev = {
        "cache": dict(bm25_index._cache),
        "dirty": set(bm25_index._dirty),
        "rev": dict(bm25_index._rev),
        "tasks": dict(bm25_index._build_tasks),
        "errors": dict(bm25_index._errors),
    }
    with bm25_index._lock:
        bm25_index._cache.clear()
        bm25_index._dirty.clear()
        bm25_index._rev.clear()
        bm25_index._errors.clear()
        for t in list(bm25_index._build_tasks.values()):
            t.cancel()
        bm25_index._build_tasks.clear()
    yield
    with bm25_index._lock:
        bm25_index._cache.update(prev["cache"])
        bm25_index._dirty.update(prev["dirty"])
        bm25_index._rev.update(prev["rev"])
        bm25_index._errors.update(prev["errors"])
        bm25_index._build_tasks.update(prev["tasks"])


def _fake_chroma(monkeypatch, chunks_provider):
    """Chroma'yi taklit eder: her çağrıda `chunks_provider()` sonucunu döndürür."""
    import shared.services.chroma_store as chroma_store

    async def fake_get(ws_id):
        await asyncio.sleep(0)  # gerçek I/O benzeri dilim (yarış testleri için)
        return [{"text": t} for t in chunks_provider()]

    monkeypatch.setattr(chroma_store, "get_workspace_chunks", fake_get)


@pytest.mark.anyio
async def test_cold_start_builds_and_caches(bind_settings, reset_index, monkeypatch):
    bind_settings()
    _fake_chroma(monkeypatch, lambda: ["birinci belge", "ikinci belge"])
    index, chunks = await bm25_index.get_index("ws-1")
    assert isinstance(index, BM25Okapi)
    assert [c["text"] for c in chunks] == ["birinci belge", "ikinci belge"]
    assert "ws-1" in bm25_index._cache
    assert "ws-1" not in bm25_index._dirty


@pytest.mark.anyio
async def test_invalidate_then_stale_serve_then_rebuild(
    bind_settings, reset_index, monkeypatch
):
    bind_settings()
    _fake_chroma(monkeypatch, lambda: ["eski metin"])
    await bm25_index.get_index("ws-1")

    # Belge değişti → invalidate
    chunks = ["eski metin", "yeni eklenen belge"]
    _fake_chroma(monkeypatch, lambda: chunks)
    bm25_index.invalidate("ws-1")
    assert "ws-1" in bm25_index._dirty

    # İlk get_index: bayat servis eder (eski corpus) ve rebuild'i arka plana atar
    index, old_chunks = await bm25_index.get_index("ws-1")
    assert [c["text"] for c in old_chunks] == ["eski metin"]

    # Arka plan rebuild'in tamamlanmasını bekle (polling — thread + task)
    for _ in range(100):
        with bm25_index._lock:
            if "ws-1" not in bm25_index._dirty:
                break
        await asyncio.sleep(0.01)
    assert "ws-1" not in bm25_index._dirty

    index2, new_chunks = await bm25_index.get_index("ws-1")
    assert [c["text"] for c in new_chunks] == ["eski metin", "yeni eklenen belge"]
    assert index2 is index or index2 is not None


@pytest.mark.anyio
async def test_single_build_task_per_workspace(bind_settings, reset_index, monkeypatch):
    bind_settings()
    slow = threading.Event()

    import shared.services.chroma_store as chroma_store

    async def slow_get(ws_id):
        slow.wait(2)  # build'i havada tut → ikinci çağrı aynı task'ı bulsun
        return []

    monkeypatch.setattr(chroma_store, "get_workspace_chunks", slow_get)

    t1 = bm25_index._schedule_rebuild("ws-7")
    t2 = bm25_index._schedule_rebuild("ws-7")
    assert t1 is t2  # in-flight task yeniden kurulmaz
    slow.set()
    await t1


@pytest.mark.anyio
async def test_clear_workspace_drops_state(bind_settings, reset_index, monkeypatch):
    bind_settings()
    _fake_chroma(monkeypatch, lambda: ["metin"])
    await bm25_index.get_index("ws-9")
    bm25_index.clear_workspace("ws-9")
    with bm25_index._lock:
        assert "ws-9" not in bm25_index._cache
        assert "ws-9" not in bm25_index._dirty
    # Silinen workspace soğuk başlangıç gibi yeniden kurulur (sonraki sorguda)
    index, chunks = await bm25_index.get_index("ws-9")
    assert index is not None
    assert [c["text"] for c in chunks] == ["metin"]


@pytest.mark.anyio
async def test_chroma_error_raises_on_cold_start(bind_settings, reset_index, monkeypatch):
    bind_settings()
    import shared.services.chroma_store as chroma_store

    class FakeChromaError(RuntimeError):
        pass

    async def boom(ws_id):
        raise FakeChromaError("chroma çöküyor")

    monkeypatch.setattr(chroma_store, "get_workspace_chunks", boom)

    with pytest.raises(FakeChromaError):
        await bm25_index.get_index("ws-boom")
    with bm25_index._lock:
        assert "ws-boom" not in bm25_index._cache  # bayat veri yok


@pytest.mark.anyio
async def test_stale_cache_survives_rebuild_failure(
    bind_settings, reset_index, monkeypatch
):
    bind_settings()
    _fake_chroma(monkeypatch, lambda: ["sağlam metin"])
    await bm25_index.get_index("ws-x")

    # Rebuild artık patlıyor — bayat cache korunmalı, hata yutulmalı
    import shared.services.chroma_store as chroma_store

    async def boom(ws_id):
        raise RuntimeError("arıza")

    monkeypatch.setattr(chroma_store, "get_workspace_chunks", boom)
    bm25_index.invalidate("ws-x")

    index, chunks = await bm25_index.get_index("ws-x")
    assert index is not None
    assert [c["text"] for c in chunks] == ["sağlam metin"]  # bayat serve devam
    with bm25_index._lock:
        assert "ws-x" in bm25_index._dirty  # bir sonraki sorgu tekrar deneyecek