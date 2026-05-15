import logging
import os
import threading
from typing import List
import numpy as np

from app.core.tokenizer_patch import apply_tokenizer_patch

apply_tokenizer_patch()

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
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

            use_fp16 = settings.EMBEDDING_USE_FP16 and device != "cpu"

            if use_fp16:
                try:
                    import torch
                    logger.info(f"加载 Embedding 模型: {local_path} (device={device}, fp16=True)")
                    self._model = SentenceTransformer(
                        local_path,
                        device=device,
                        local_files_only=True,
                        model_kwargs={"torch_dtype": torch.float16},
                    )
                except Exception:
                    logger.warning("float16 加载失败，回退到 float32")
                    logger.info(f"加载 Embedding 模型: {local_path} (device={device}, fp32)")
                    self._model = SentenceTransformer(
                        local_path,
                        device=device,
                        local_files_only=True,
                    )
            else:
                logger.info(f"加载 Embedding 模型: {local_path} (device={device}, fp32)")
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

    def _validate_token_lengths(self, texts: List[str]) -> None:
        self._load_model()
        tokenizer = self._model.tokenizer
        from app.core.config import settings
        model_max = getattr(self._model, 'max_seq_length', 512)
        max_tokens = getattr(settings, 'BGE_MAX_TOKENS', 450)
        if max_tokens >= model_max:
            max_tokens = model_max - 50
            logger.info(f"[向量化] BGE_MAX_TOKENS={settings.BGE_MAX_TOKENS} >= model_max={model_max}, 自动调整为 {max_tokens}")

        over_count = 0
        max_found = 0

        for i, text in enumerate(texts):
            tokens = tokenizer.encode(text, add_special_tokens=True)
            token_count = len(tokens)
            if token_count > max_found:
                max_found = token_count
            if token_count > max_tokens:
                over_count += 1
                if over_count <= 3:
                    content_preview = text[:60].replace("\n", "\\n")
                    logger.warning(
                        f"[向量化] ⚠️ 文本块 #{i} token数={token_count} 超过阈值{max_tokens} "
                        f"(模型上限={model_max})，将被截断。"
                        f"建议减小 CHUNK_SIZE。内容预览: {content_preview}..."
                    )

        if over_count > 0:
            logger.warning(
                f"[向量化] ⚠️ {over_count}/{len(texts)} 个文本块 token 超限 "
                f"(阈值={max_tokens}, 最大={max_found}, 模型上限={model_max})"
            )
        else:
            logger.info(
                f"[向量化] ✅ token 验证通过 ({len(texts)}个, 最大token={max_found}/{max_tokens})"
            )

    def encode(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        self._validate_token_lengths(texts)
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