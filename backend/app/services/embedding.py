import logging
import os
import threading
from typing import List
import numpy as np

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
os.environ.setdefault("HF_HOME", _MODELS_DIR)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", _MODELS_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(_MODELS_DIR, "transformers"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.makedirs(_MODELS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


class EmbeddingService:
    _instance = None
    _model = None
    _loaded = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return

            from app.core.config import settings
            from sentence_transformers import SentenceTransformer

            model_name = settings.EMBEDDING_MODEL
            device = settings.EMBEDDING_DEVICE

            logger.info(f"加载 Embedding 模型: {model_name} (device={device})")
            self._model = SentenceTransformer(model_name, device=device)
            self._loaded = True
            logger.info("Embedding 模型加载完成")

    def ensure_loaded(self):
        self._load_model()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def encode(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=16,
        )
        return embeddings.tolist()

    def encode_single(self, text: str) -> List[float]:
        results = self.encode([text])
        return results[0]

    @property
    def dim(self) -> int:
        from app.core.config import settings
        return settings.EMBEDDING_DIM


embedding_service = EmbeddingService()
