"""Ortak test kurulumu — repo kökü + servis paketleri sys.path'e eklenir.

Tek venv (web-api) üzerinden çalıştırılır:
    cd web-api && uv run --no-sync pytest ../tests -q
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "web-api"), str(ROOT / "worker")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shared.core import config as shared_config  # noqa: E402


@pytest.fixture
def anyio_backend():
    """Async testler yalnızca asyncio backend'de çalışır (trio yok)."""
    return "asyncio"


@pytest.fixture
def bind_settings(monkeypatch):
    """`shared.core.config`'e sahte servis ayarları bağlar; test sonrası eskiyi geri yükler.

    Kullanım: `settings = bind_settings(storage_dir="tmp", bm25_stem_cap=5)` — modül
    fonksiyonları `get_settings()` ile istenen alanlara erişir.
    """
    prev = shared_config._current

    def _bind(**overrides):
        defaults = dict(
            storage_dir="/tmp/folyo-storage",
            redis_url="redis://localhost:6379/0",
            bm25_stem_min=4,
            bm25_stem_cap=24,
            auth_secret="test-secret",
            auth_token_ttl_hours=24,
        )
        defaults.update(overrides)
        ns = SimpleNamespace(**defaults)
        shared_config.bind(ns)
        return ns

    yield _bind
    shared_config._current = prev