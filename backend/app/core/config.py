import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "HeatAI"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    SECRET_KEY: str = "heatai-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+asyncpg://heatai:heatai123@localhost:5432/heatai"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://heatai:heatai123@localhost:5432/heatai"

    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_MODEL: str = "qwen-max"

    MILVUS_URI: str = ""
    MILVUS_TOKEN: str = ""
    MILVUS_COLLECTION_NAME: str = "knowledge_base"

    MODELS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "..", "models")

    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIM: int = 1024

    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_DEVICE: str = "cpu"

    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    BM25_RETRIEVAL_TOP_K: int = 50
    HYBRID_BM25_WEIGHT: float = 0.4
    HYBRID_VECTOR_WEIGHT: float = 0.6

    RERANK_RECALL_TOP_K: int = 20
    RERANK_COARSE_TOP_K: int = 10
    RERANK_FINAL_TOP_K: int = 8
    RERANK_BM25_WEIGHT: float = 0.3
    RERANK_BGE_WEIGHT: float = 0.7

    SIMILARITY_THRESHOLD: float = 0.35

    CONTEXT_MAX_CHUNK_CHARS: int = 800
    CONTEXT_MAX_TOTAL_CHARS: int = 6000

    LLM_TEMPERATURE: float = 0.15

    UPLOAD_DIR: str = "./uploads"

    LOG_LEVEL: str = "INFO"

    MEMORY_LLM_MODEL: str = "qwen-turbo"
    MEMORY_EXTRACT_TRIGGER_ROUNDS: int = 5
    MEMORY_COMPRESS_THRESHOLD_CHARS: int = 5000
    MEMORY_MAX_CONTEXT_CHARS: int = 3000
    MEMORY_DECAY_HALF_LIFE_DAYS: int = 30
    MEMORY_EMOTION_MAX_ENTRIES: int = 20
    MEMORY_SESSION_SNAPSHOT_MAX: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
