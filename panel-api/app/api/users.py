"""Kullanıcı yönetimi — yalnızca admin (panel token'ı ile erişilir).

web-api'den taşındı; `create_user` kaydı bcrypt hash ile yazar, `list_users`
hash'i asla dışarı sızdırmaz. Giriş akışı ayrıca `api/auth.py`'de (login/me).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select as sm_select

from ..core.database import get_factory
from ..core.security import hash_password, require_auth
from shared.models import User
from ..schemas.user import UserCreate

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_auth)])


def _out(u: User) -> dict:
    return {
        "id": str(u.id),
        "username": u.username,
        "user_type": u.user_type.value,
        "created_at": u.created_at.isoformat(),
    }


@router.post("")
async def create_user(body: UserCreate):
    username = body.username.strip()
    if not username:
        raise HTTPException(422, "Kullanıcı adı boş olamaz.")
    try:
        password_hash = hash_password(body.password)
    except ValueError as exc:
        # Boş şifre VEYA bcrypt 72 byte sınırı (çok uzun/unicode şifre).
        raise HTTPException(422, str(exc)) from exc

    async with get_factory()() as s:
        existing = (
            await s.execute(sm_select(User).where(User.username == username))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(409, "Bu kullanıcı adı zaten kayıtlı.")
        user = User(username=username, password_hash=password_hash, user_type=body.user_type)
        s.add(user)
        await s.commit()
        await s.refresh(user)
    return _out(user)


@router.get("")
async def list_users():
    async with get_factory()() as s:
        rows = (await s.execute(sm_select(User).order_by(User.username))).scalars().all()
    return {"users": [_out(u) for u in rows]}