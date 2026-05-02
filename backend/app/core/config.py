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
    DASHSCOPE_MODEL: str = "qwen3-max"

    MILVUS_DB_PATH: str = "./milvus_data"
    MILVUS_COLLECTION_NAME: str = "knowledge_base"

    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIM: int = 1024

    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    UPLOAD_DIR: str = "./uploads"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
