"""shared.core.taskq — ARQ Redis ayar derlemesi (pool'a dokunmaz, saf DSN çözümü)."""

from shared.core import taskq


def test_redis_settings_from_dsn(bind_settings):
    bind_settings(redis_url="redis://cache.example:6380/3")
    rs = taskq.redis_settings()
    assert rs.host == "cache.example"
    assert rs.port == 6380


def test_redis_settings_default_port(bind_settings):
    bind_settings(redis_url="redis://localhost:6379/0")
    rs = taskq.redis_settings()
    assert rs.host == "localhost"
    assert rs.port == 6379