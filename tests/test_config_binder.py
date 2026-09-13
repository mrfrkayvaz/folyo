"""shared.core.config — servis ayarları bağlayıcısı."""

import pytest

from shared.core import config


def test_get_settings_before_bind_raises(monkeypatch):
    monkeypatch.setattr(config, "_current", None)
    with pytest.raises(RuntimeError, match="bind edilmedi"):
        config.get_settings()


def test_bind_then_get_returns_same_object(bind_settings):
    ns = bind_settings(storage_dir="x")
    assert config.get_settings() is ns


def test_rebind_overwrites(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(config, "_current", None)
    config.bind(SimpleNamespace(a=1))
    assert config.get_settings().a == 1
    config.bind(SimpleNamespace(a=2))
    assert config.get_settings().a == 2