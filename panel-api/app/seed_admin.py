"""Admin kullanıcı seed'ı — idempotent (güvenle tekrar çalıştırılabilir).

Şema sahibi artık panel-api olduğundan seed da burada yaşar.

Kullanım (panel-api container'ı içinde, /app dizininden):
    uv run --no-sync python -m app.seed_admin

Env kaynağı: panel-api/.env → `ADMIN_USERNAME` + `ADMIN_PASSWORD`
(compose bu dosyayı env_file olarak taşır; pydantic-settings okur). Kurallar:

1. users tablosunda tipi `admin` olan biri zaten varsa → no-op (idempotent).
2. Admin yoksa ve `ADMIN_USERNAME` boşta değilse → yeni kayıt (bcrypt hash ile).
3. Admin yoksa ama `ADMIN_USERNAME` aynı isimle `user` tipinde kayıtlıysa →
   o hesap admin'e yükseltilir, şifresi `ADMIN_PASSWORD` ile güncellenir.
"""

import asyncio

from sqlalchemy import select

from .core.config import get_settings
from .core.database import get_factory, init_db
from shared.core.enums import UserType
from .core.security import hash_password
from shared.models import User


def _out(message: str) -> None:
    """CLI çıktısı — init_db'i çalıştıran alembic root logger seviyesini WARNING'a
    çekebildiğinden INFO logları yutulabilir; sonuçlar her durumda stdout'ta basılır."""
    print(f"[seed.admin] {message}", flush=True)


async def seed_admin() -> bool:
    settings = get_settings()
    username = settings.admin_username.strip()
    password = settings.admin_password
    if not username or not password:
        _out(
            "ADMIN_USERNAME veya ADMIN_PASSWORD boş — seed yapılamadı. "
            "panel-api/.env dosyasına ikisini de ekleyin."
        )
        return False

    async with get_factory()() as s:
        admins = (
            await s.execute(select(User).where(User.user_type == UserType.admin))
        ).scalars().all()
        if admins:
            _out(f"Admin kullanıcı zaten mevcut ({admins[0].username}) — seed atlandı (idempotent).")
            return True

        existing = (
            await s.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()
        if existing:
            existing.user_type = UserType.admin
            existing.password_hash = hash_password(password)
            s.add(existing)
            await s.commit()
            _out(f"Mevcut kullanıcı '{username}' admin'e yükseltildi, şifresi güncellendi.")
            return True

        user = User(username=username, password_hash=hash_password(password), user_type=UserType.admin)
        s.add(user)
        await s.commit()
        _out(f"Admin kullanıcı '{username}' oluşturuldu (type=admin).")
        return True


async def _main() -> bool:
    # Şema yokken bile seed çalışabilsin: önce migrasyonları uygula (aynı event loop).
    await init_db()
    return await seed_admin()


if __name__ == "__main__":
    ok = asyncio.run(_main())
    raise SystemExit(0 if ok else 1)