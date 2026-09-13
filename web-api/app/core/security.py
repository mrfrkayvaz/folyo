"""Web API kimlik doğrulama — HMAC imzalı bearer token + bcrypt (users tablosu, yalnız admin).

Panel ile aynı sözleşme: paylaşılan `shared.models.User` + `shared.core.enums.UserType`;
şifre hash'i bcrypt ($2b$...). Anahtar `AUTH_SECRET` (web-api kendi env'i); set edilmezse
dev fallback + uyarı (prod'da AUTH_SECRET gerekli).
"""

import base64
import hashlib
import hmac
import json
import logging
import time

import bcrypt
from fastapi import Header, HTTPException

from .config import get_settings

LOG = logging.getLogger("uvicorn.error.web.security")

_DEV_SECRET = "folyo-web-dev-insecure-secret-do-not-use-in-prod"
_DEV_SECRET_WARNED = False


def _secret() -> bytes:
    global _DEV_SECRET_WARNED
    secret = get_settings().auth_secret.strip()
    if not secret:
        if not _DEV_SECRET_WARNED:
            _DEV_SECRET_WARNED = True
            LOG.warning("[auth] AUTH_SECRET ayarlanmamış — dev fallback anahtarı kullanılıyor. Prod'da set edin!")
        secret = _DEV_SECRET
    return secret.encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_token(*, user_id: str, username: str, user_type: str) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "user_type": user_type,
        "iat": now,
        "exp": now + max(1, int(settings.auth_token_ttl_hours)) * 3600,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str) -> dict | None:
    try:
        body_b64, sig_b64 = token.split(".")
        expected = _b64(hmac.new(_secret(), body_b64.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig_b64):
            return None
        payload = json.loads(_unb64(body_b64).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def require_auth(authorization: str | None = Header(default=None)) -> dict:
    """Korumalı endpoint dependency'si: `Authorization: Bearer <token>` + admin şartı."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Giriş gerekli: Authorization: Bearer <token>")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Geçersiz veya süresi dolmuş oturum token'ı.")
    if payload.get("user_type") != "admin":
        raise HTTPException(403, "Bu işlem için admin yetkisi gerekli.")
    return payload