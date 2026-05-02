from contextlib import asynccontextmanager
import threading
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router

logger = logging.getLogger(__name__)


def _preload_model():
    from app.services.embedding import embedding_service
    logger.info("正在预加载 Embedding 模型，首次下载可能需要几分钟...")
    embedding_service.ensure_loaded()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    threading.Thread(target=_preload_model, daemon=True).start()

    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API", "version": settings.VERSION}


@app.get("/health")
async def health():
    return {"status": "ok"}
