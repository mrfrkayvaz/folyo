from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import api_router

app = FastAPI(
    title="Folyo Panel API",
    description="Yönetim görünümü — workspaces, dokümanlar, süreç ve chunk'lar (okuma amaçlı).",
    version="0.1.0",
)

app.include_router(api_router)