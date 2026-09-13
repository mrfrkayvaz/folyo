from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings

# Ortak (shared) modüller bu servisin Settings nesnesini kullanır — shared importları
# bind'den SONRA gelmelidir (embeddings modül-importta get_settings() çağırır).
from shared.core import config as _shared_config

_shared_config.bind(get_settings())

from .api import api_router
from .core.database import reset_interrupted_jobs
from .services.jobs.recover import recover_orphaned_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Şema migrasyonu panel-api yönetir (init_db orada); bu servis yalnızca kuyruk
    # durumlarını sıfırlar + restart/kesintiyle ölmüş embed görevlerini yeniden zamanlar.
    await reset_interrupted_jobs()
    await recover_orphaned_jobs()
    yield


app = FastAPI(
    title="Folyo API",
    description="Belge Analiz ve Soru-Cevap (workspace'li, streaming RAG)",
    version="0.3.0",
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