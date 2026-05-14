import logging
import os
import threading
from typing import List, Tuple

from app.core.tokenizer_patch import apply_tokenizer_patch

apply_tokenizer_patch()

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
os.environ.setdefault("HF_HUB_CACHE", _MODELS_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(_MODELS_DIR, "transformers"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.makedirs(_MODELS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


def _resolve_local_reranker(settings_model_dir: str, model_name: str) -> str:
    models_dir = os.path.abspath(settings_model_dir)
    model_slug = model_name.split("/")[-1]
    local_candidate = os.path.join(models_dir, model_slug)
    if os.path.isdir(local_candidate):
        config_file = os.path.join(local_candidate, "config.json")
        model_file = os.path.join(local_candidate, "model.safetensors")
        pytorch_file = os.path.join(local_candidate, "pytorch_model.bin")
        if os.path.isfile(config_file) and (os.path.isfile(model_file) or os.path.isfile(pytorch_file)):
            logger.info(f"Using local reranker model: {local_candidate}")
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
                    logger.info(f"Using local reranker model from HF cache: {snapshot_path}")
                    return snapshot_path

    if os.path.isabs(model_name) and os.path.isdir(model_name):
        return model_name

    logger.info(f"No local reranker model found, will use: {model_name}")
    return model_name


class CrossRerankerService:
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
            from FlagEmbedding import FlagReranker

            model_name = settings.RERANKER_MODEL
            device = settings.RERANKER_DEVICE

            local_path = _resolve_local_reranker(settings.MODELS_DIR, model_name)

            logger.info(f"Loading Cross-Encoder reranker: {local_path} (device={device})")
            self._model = FlagReranker(
                local_path,
                use_fp16=(device != "cpu"),
                devices=[device] if device != "cpu" else None,
            )
            self._loaded = True
            logger.info("Cross-Encoder reranker loaded")

    def ensure_loaded(self):
        self._load_model()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def compute_scores(
        self,
        query: str,
        candidates: List[Tuple[str, str]],
        normalize: bool = True,
    ) -> List[float]:
        self._load_model()

        pairs = [[query, text] for _, text in candidates]
        scores = self._model.compute_score(pairs, normalize=normalize)

        if isinstance(scores, float):
            scores = [scores]
        return list(scores)


cross_reranker_service = CrossRerankerService()