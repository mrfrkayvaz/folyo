"""web-api app.core.security — HMAC bearer token + bcrypt + require_auth.

`get_settings` sahte nesneyle değiştirilir; gerçek env/DB yok. Zaman, modül
içindeki `time` özniteliği dondurularak kontrol edilir (expiry testi).
"""

from types import SimpleNamespace

import bcrypt
import pytest
from fastapi import HTTPException

from app.core import security


@pytest.fixture
def auth_settings(monkeypatch):
    def _fake_settings():
        return SimpleNamespace(auth_secret="test-secret-abc", auth_token_ttl_hours=24)

    monkeypatch.setattr(security, "get_settings", _fake_settings)
    return _fake_settings()


def test_token_roundtrip(auth_settings):
    tok = security.create_token(user_id="u1", username="ad", user_type="admin")
    payload = security.verify_token(tok)
    assert payload is not None
    assert payload["sub"] == "u1"
    assert payload["username"] == "ad"
    assert payload["user_type"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_wrong_secret_rejected(auth_settings):
    # Token A ANHTARIYLA üretilir, B anahtarıyla doğrulanır → red
    tok = security.create_token(user_id="u1", username="a", user_type="admin")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: SimpleNamespace(auth_secret="other-secret", auth_token_ttl_hours=24),
    )
    try:
        assert security.verify_token(tok) is None
    finally:
        monkeypatch.undo()


def test_tampered_signature_rejected(auth_settings):
    tok = security.create_token(user_id="u1", username="a", user_type="admin")
    body, sig = tok.split(".")
    bad_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
    assert security.verify_token(f"{body}.{bad_sig}") is None


def test_malformed_token_rejected(auth_settings):
    assert security.verify_token("") is None
    assert security.verify_token("tek-parça") is None
    assert security.verify_token("a.b") is None
    assert security.verify_token("a.b.c") is None


def test_expired_token_rejected(monkeypatch, auth_settings):
    class FakeClock:
        def __init__(self, now: float):
            self._now = now

        def time(self) -> float:
            return self._now

    T0 = 1_700_000_000.0
    monkeypatch.setattr(security, "time", FakeClock(T0))
    tok = security.create_token(user_id="u1", username="a", user_type="admin")

    # Süre doldu (24 saat + 10 sn sonra)
    monkeypatch.setattr(security, "time", FakeClock(T0 + 24 * 3600 + 10))
    assert security.verify_token(tok) is None


def test_verify_password_roundtrip():
    hashed = bcrypt.hashpw(b"gizli", bcrypt.gensalt()).decode("ascii")
    assert security.verify_password("gizli", hashed) is True
    assert security.verify_password("yanlis", hashed) is False


def test_verify_password_malformed_hash_is_false():
    assert security.verify_password("x", "çöp-hash") is False
    assert security.verify_password("x", "") is False


def test_require_auth_missing_header():
    with pytest.raises(HTTPException) as ei:
        security.require_auth(None)
    assert ei.value.status_code == 401


def test_require_auth_wrong_scheme(auth_settings):
    with pytest.raises(HTTPException) as ei:
        security.require_auth("Basic abc")
    assert ei.value.status_code == 401


def test_require_auth_garbage_token(auth_settings):
    with pytest.raises(HTTPException) as ei:
        security.require_auth("Bearer olmayan-token")
    assert ei.value.status_code == 401


def test_require_auth_non_admin_forbidden(auth_settings):
    tok = security.create_token(user_id="k1", username="k", user_type="user")
    with pytest.raises(HTTPException) as ei:
        security.require_auth(f"Bearer {tok}")
    assert ei.value.status_code == 403


def test_require_auth_admin_passes(auth_settings):
    tok = security.create_token(user_id="a1", username="admin", user_type="admin")
    payload = security.require_auth(f"Bearer {tok}")
    assert payload["user_type"] == "admin"
    assert payload["sub"] == "a1"