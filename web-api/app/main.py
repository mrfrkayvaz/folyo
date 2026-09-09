from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import api_router
from .core.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Folyo API",
    description="Belge Analiz ve Soru-Cevap (workspace'li, streaming RAG)",
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(api_router)