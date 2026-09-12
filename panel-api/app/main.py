from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .core.config import get_settings

app = FastAPI(
    title="Folyo Panel API",
    description="Yönetim görünümü — workspaces, dokümanlar, süreç ve chunk'lar (okuma amaçlı).",
    version="0.1.0",
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