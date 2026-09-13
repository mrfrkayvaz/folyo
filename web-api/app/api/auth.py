"""Web girişi — yalnızca admin kullanıcılar (users tablosu, panel ile aynı sözleşme).

Login başarılı + user_type=admin → HMAC imzalı bearer token; web frontend bu token'ı
tüm isteklere `Authorization` header'ı olarak ekler (`require_auth` doğrular).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..core.database import get_factory
from ..core.security import create_token, require_auth, verify_password
from shared.core.enums import UserType
from shared.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


@router.post("/login")
async def login(body: LoginRequest):
    async with get_factory()() as s:
        user = (
            await s.execute(select(User).where(User.username == body.username.strip()))
        ).scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Kullanıcı adı veya şifre hatalı.")
    if user.user_type != UserType.admin:
        raise HTTPException(403, "Web paneline yalnızca admin kullanıcılar giriş yapabilir.")

    token = create_token(user_id=str(user.id), username=user.username, user_type=user.user_type.value)
    return {"token": token, "username": user.username, "user_type": user.user_type.value}


@router.get("/me")
async def me(auth: dict = Depends(require_auth)):
    """Token geçerliliğini doğrular; frontend oturum geri yüklemede kullanır."""
    return {"username": auth["username"], "user_type": auth["user_type"]}