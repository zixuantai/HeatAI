import logging
import os
import threading
from typing import List
import numpy as np

from app.core.tokenizer_patch import apply_tokenizer_patch

apply_tokenizer_patch()

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
os.environ.setdefault("HF_HUB_CACHE", _MODELS_DIR)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", _MODELS_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(_MODELS_DIR, "transformers"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ["HF_HUB_OFFLINE"] = "1"
os.makedirs(_MODELS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def _resolve_local_model(settings_model_dir: str, model_name: str) -> str:
    models_dir = os.path.abspath(settings_model_dir)
    model_slug = model_name.split("/")[-1]
    local_candidate = os.path.join(models_dir, model_slug)
    if os.path.isdir(local_candidate):
        config_file = os.path.join(local_candidate, "config.json")
        if os.path.isfile(config_file):
            logger.info(f"Using local embedding model: {local_candidate}")
            return local_candidate

    hf_cache_candidate = os.path.join(models_dir, f"models--{model_name.replace('/', '--')}")
    if os.path.isdir(hf_cache_candidate):
        snapshots_dir = os.path.join(hf_cache_candidate, "snapshots")
        if os.path.isdir(snapshots_dir):
            for snapshot in sorted(os.listdir(snapshots_dir), reverse=True):
                snapshot_path = os.path.join(snapshots_dir, snapshot)
                config_file = os.path.join(snapshot_path, "config.json")
                model_file = os.path.join(snapshot_path, "model.safetensors")
                pytorch_file = os.path.join(snapshot_path, "pytorch_model.bin")
                if os.path.isfile(config_file) and (os.path.isfile(model_file) or os.path.isfile(pytorch_file)):
                    logger.info(f"Using local embedding model from HF cache: {snapshot_path}")
                    return snapshot_path

    if os.path.isabs(model_name) and os.path.isdir(model_name):
        return model_name

    logger.info(f"No local embedding model found, will use: {model_name}")
    return model_name


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

            local_path = _resolve_local_model(settings.MODELS_DIR, model_name)

            logger.info(f"加载 Embedding 模型: {local_path} (device={device})")
            self._model = SentenceTransformer(
                local_path,
                device=device,
                local_files_only=True,
            )
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
