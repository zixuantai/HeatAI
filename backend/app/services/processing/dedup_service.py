import hashlib
import logging
import re
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")


class MinHashDedupService:

    def __init__(self, threshold: float = 0.85, num_perm: int = 128):
        self.threshold = threshold
        self.num_perm = num_perm
        self._hashes: List[List[int]] = []

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

    def _minhash_signature(self, shingles: Set[str]) -> List[int]:
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

    def deduplicate(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return chunks

        kept: List[Dict[str, Any]] = []
        removed_count = 0

        for chunk in chunks:
            content = chunk.get("content", "")
            k = self._detect_k(content)
            shingles = self._shingle_text(content, k=k)
            sig = self._minhash_signature(shingles)

            is_dup = False
            for existing_sig in self._hashes:
                sim = self._jaccard_similarity(sig, existing_sig)
                if sim >= self.threshold:
                    is_dup = True
                    break

            if is_dup:
                removed_count += 1
                if removed_count <= 3:
                    preview = content[:50].replace("\n", "\\n")
                    logger.info(f"[去重] 跳过重复 chunk (内容预览: {preview}...)")
                continue

            kept.append(chunk)
            self._hashes.append(sig)

        if removed_count > 0:
            logger.info(f"[去重] {len(chunks)} → {len(kept)} chunks, 移除 {removed_count} 个 (阈值={self.threshold})")

        return kept

    def reset(self):
        self._hashes = []