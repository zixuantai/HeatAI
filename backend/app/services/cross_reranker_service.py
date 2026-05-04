import logging
import os
import threading
from typing import List, Tuple

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
os.environ.setdefault("HF_HUB_CACHE", _MODELS_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(_MODELS_DIR, "transformers"))
os.makedirs(_MODELS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


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

            logger.info(f"Loading Cross-Encoder reranker: {model_name} (device={device})")
            self._model = FlagReranker(
                model_name,
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
