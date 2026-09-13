"""Panel API kimlik doğrulama — HMAC imzalı taşıyıcı (bearer) token + bcrypt şifre.

Token biçimi: `payload_b64.sig_b64` (JWT benzeri ama bağımlılıksız — stdlib
`hmac` + `hashlib.sha256`). Payload: `{sub, username, user_type, iat, exp}`.
Anahtar `AUTH_SECRET`; set edilmemişse dev fallback anahtarı kullanılır ve
uyarılır (prod'da Coolify env'i eklenmeli — token'lar restart'a dayanmaz).

Panel koruması kuralı: `require_auth` dependency'si her korumalı router'a
takılır — geçerli token + `user_type == admin` şartı. Login endpoint'i zaten
yalnızca admin'e token üretir; bu şart savunma derinliğidir.
"""

import base64
import hashlib
import hmac
import json
import logging
import time

import bcrypt
from fastapi import Header, HTTPException

from ..core.config import get_settings

LOG = logging.getLogger("uvicorn.error.panel.security")

# Yalnızca geliştirme: AUTH_SECRET set edilmemişken kullanılır (kararlı dev oturumu).
_DEV_SECRET = "folyo-panel-dev-insecure-secret-do-not-use-in-prod"
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
    """İmza + süre doğrulaması; bozuksa/süresi dolduysa `None`."""
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


def hash_password(plain: str) -> str:
    """bcrypt hash — users tablosuyla uyumlu ($2b$12$...). Boş/çok uzun girdi ValueError."""
    if not plain:
        raise ValueError("Şifre boş olamaz.")
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt doğrulama — web-api'nin users tablosu formatıyla uyumlu ($2b$...)."""
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