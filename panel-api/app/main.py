import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings

# Ortak (shared) modüller panel-api'nin Settings nesnesini kullanır.
from shared.core import config as _shared_config

_shared_config.bind(get_settings())

from .api import api_router
from .core.database import init_db


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    # Şema sahibi panel-api: startupta alembic migration'larını uygula.
    await init_db()
    yield


app = FastAPI(
    title="Folyo Panel API",
    description="Yönetim görünümü — workspaces, dokümanlar, süreç ve chunk'lar; "
    "şema/migrasyon + kullanıcı yönetimi sahibi.",
    version="0.2.0",
    lifespan=lifespan,
)

_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
if _origins:
    # Dev'de frontend farklı porttan (5173/5174) API'ye doğrudan istek atabilir.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)