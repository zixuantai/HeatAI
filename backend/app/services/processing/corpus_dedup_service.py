import hashlib
import json
import logging
import re
from typing import List, Dict, Any, Set

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")


class CorpusDedupService:

    def __init__(self, threshold: float = 0.85, num_perm: int = 128):
        self.threshold = threshold
        self.num_perm = num_perm

    def _detect_k(self, text: str) -> int:
        cjk_count = len(_CJK_RE.findall(text))
        total_chars = len(text.replace(" ", ""))
        if total_chars > 0 and cjk_count / max(total_chars, 1) > 0.3:
            return 2
        return 3

    def _shingle_text(self, text: str, k: int = 3) -> Set[str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) < k:
            return {cleaned}
        return {cleaned[i:i + k] for i in range(len(cleaned) - k + 1)}

    def _stable_hash(self, s: str, seed: int) -> int:
        data = f"{seed}:{s}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(data).digest()[:4], "big")

    def compute_signature(self, text: str) -> List[int]:
        k = self._detect_k(text)
        shingles = self._shingle_text(text, k=k)
        sig = []
        for i in range(self.num_perm):
            min_val = 0xFFFFFFFF
            for s in shingles:
                hv = self._stable_hash(s, i)
                if hv < min_val:
                    min_val = hv
            sig.append(min_val)
        return sig

    def _jaccard_similarity(self, sig1: List[int], sig2: List[int]) -> float:
        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)

    @staticmethod
    def signature_to_str(sig: List[int]) -> str:
        return json.dumps(sig)

    @staticmethod
    def str_to_signature(s: str) -> List[int]:
        return json.loads(s)

    async def check_duplicate(
        self,
        db: AsyncSession,
        user_id: str,
        parsed_text: str,
    ) -> Document | None:
        text_len = len(parsed_text.strip())
        if text_len < 200:
            return None

        new_sig = self.compute_signature(parsed_text)

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.minhash_sig.isnot(None),
                Document.status == "completed",
            )
        )
        existing_docs = result.scalars().all()

        for doc in existing_docs:
            if not doc.minhash_sig:
                continue
            try:
                existing_sig = self.str_to_signature(doc.minhash_sig)
            except json.JSONDecodeError:
                continue
            sim = self._jaccard_similarity(new_sig, existing_sig)
            if sim >= self.threshold:
                logger.info(
                    f"[语料去重] 检测到相似文档: '{doc.original_filename}' "
                    f"(相似度={sim:.2%}, 阈值={self.threshold})"
                )
                return doc

        return None

    async def index_signature(self, db: AsyncSession, doc_id: str, text: str):
        try:
            sig = self.compute_signature(text)
            sig_str = self.signature_to_str(sig)
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalars().first()
            if doc:
                doc.minhash_sig = sig_str
                await db.commit()
                logger.info(f"[语料去重] 已索引文档签名: {doc_id}")
        except Exception as e:
            logger.warning(f"[语料去重] 签名索引写入失败 (doc={doc_id}): {e}")