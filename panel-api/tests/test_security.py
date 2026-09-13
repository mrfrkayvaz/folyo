"""panel-api app.core.security — web-api ile aynı HMAC/bcrypt sözleşmesi.

Panel token'ları web-api ile ortak `AUTH_SECRET` yapılandırmasından üretilir;
bu dosya panel tarafının kendi gerçeklemesini doğrular (sözleşme uyumu).
"""

from types import SimpleNamespace

import bcrypt
import pytest
from fastapi import HTTPException

from app.core import security


@pytest.fixture
def auth_settings(monkeypatch):
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: SimpleNamespace(auth_secret="panel-test-secret", auth_token_ttl_hours=24),
    )


def test_token_roundtrip_admin(auth_settings):
    tok = security.create_token(user_id="p1", username="panel", user_type="admin")
    payload = security.verify_token(tok)
    assert payload["user_type"] == "admin"
    assert payload["sub"] == "p1"


def test_token_rejects_wrong_secret(auth_settings):
    tok = security.create_token(user_id="p1", username="panel", user_type="admin")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: SimpleNamespace(auth_secret="farkli", auth_token_ttl_hours=24),
    )
    try:
        assert security.verify_token(tok) is None
    finally:
        monkeypatch.undo()


def test_tampered_token_rejected(auth_settings):
    tok = security.create_token(user_id="p1", username="a", user_type="admin")
    body, _ = tok.split(".")
    assert security.verify_token(f"{body}.bogus") is None


def test_require_auth_admin_allowed(auth_settings):
    tok = security.create_token(user_id="p1", username="a", user_type="admin")
    assert security.require_auth(f"Bearer {tok}")["user_type"] == "admin"


def test_require_auth_user_forbidden(auth_settings):
    tok = security.create_token(user_id="k1", username="k", user_type="user")
    with pytest.raises(HTTPException) as ei:
        security.require_auth(f"Bearer {tok}")
    assert ei.value.status_code == 403


def test_require_auth_missing_header(auth_settings):
    with pytest.raises(HTTPException) as ei:
        security.require_auth(None)
    assert ei.value.status_code == 401


def test_verify_password_roundtrip():
    hashed = bcrypt.hashpw(b"sifre", bcrypt.gensalt()).decode("ascii")
    assert security.verify_password("sifre", hashed) is True
    assert security.verify_password("yanlis", hashed) is False