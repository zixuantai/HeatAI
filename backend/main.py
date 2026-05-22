import os

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
os.makedirs(_MODELS_DIR, exist_ok=True)

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_CACHE", _MODELS_DIR)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", _MODELS_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(_MODELS_DIR, "transformers"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ["HF_HUB_OFFLINE"] = "1"

import asyncio
import logging
import sys

from app.core.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

for _lib in ("sentence_transformers", "transformers", "tokenizers",
             "jieba", "rank_bm25", "pymilvus", "milvus_lite",
             "httpx", "httpcore", "urllib3", "openai",
             "datasets", "huggingface_hub", "filelock"):
    logging.getLogger(_lib).setLevel(logging.WARNING)

from contextlib import asynccontextmanager
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine, Base
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.voice import router as voice_router
from app.api.v1.organizations import router as organizations_router

logger = logging.getLogger(__name__)


def _preload_model():
    from app.services.retrieval.embedding import embedding_service
    logger.info("正在加载 Embedding 模型到内存...")
    embedding_service.ensure_loaded()

    from app.services.retrieval.cross_reranker_service import cross_reranker_service
    logger.info("正在加载 Cross-Encoder Reranker 模型到内存...")
    cross_reranker_service.ensure_loaded()


def _rebuild_bm25_from_milvus():
    from app.services.retrieval.milvus_service import milvus_service
    from app.services.retrieval.bm25_service import bm25_service

    logger.info("正在检查 BM25 索引状态...")
    if bm25_service.chunk_count > 0:
        logger.info(f"BM25 索引已有 {bm25_service.chunk_count} 条数据，跳过重建")
        return

    logger.info("BM25 磁盘缓存不可用，正在从 Milvus 重建...")
    milvus_service._ensure_initialized()
    chunks = milvus_service.get_all_chunks()
    logger.info(f"Milvus 中共有 {len(chunks)} 条 chunk 记录")
    bm25_service.rebuild_from_milvus_chunks(chunks)
    logger.info(f"BM25 索引重建完成，共 {bm25_service.chunk_count} 条 chunk")


def _startup_init():
    _preload_model()
    _rebuild_bm25_from_milvus()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar TEXT"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS category VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS minhash_sig TEXT"))
        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS organization_id UUID"))
        await conn.commit()

    await asyncio.get_running_loop().run_in_executor(None, _startup_init)

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
app.include_router(voice_router, prefix=settings.API_V1_PREFIX)
app.include_router(organizations_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API", "version": settings.VERSION}


@app.get("/health")
async def health():
    return {"status": "ok"}
