# Folyo Panel API

Yönetim görünümü + **altyapı tabanı**:

- **Şema sahibi:** SQLModel modelleri (`app/models.py`) + alembic migration'ları
  (`app/alembic/`); başlangıçta `init_db` uygular (prod'da panel-api deploy'u
  migrasyonu da yürütür).
- **Kullanıcı yönetimi:** `users` tablosu; kayıt/liste (`/api/users`, sadece admin
  token'ı ile) + idempotent admin seed (`uv run python -m app.seed_admin`,
  `ADMIN_USERNAME` / `ADMIN_PASSWORD` env'leri).
- **Kimlik:** yalnızca admin girişi (`/api/auth/login`) → HMAC imzalı bearer token.
- **Okuma görünümü:** workspaces / documents / chunk'lar — aynı Postgres
  (`DATABASE_URL`) ve aynı Chroma (`CHROMA_DIR`) klasörünü okur; web-api ve
  worker bu şemayı kullanır.