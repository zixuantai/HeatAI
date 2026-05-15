import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class TextChunker:

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        base_meta = metadata or {}

        paragraphs = self._split_paragraphs(text)

        chunks_data: List[Dict[str, Any]] = []
        current_chunk = ""
        current_meta = dict(base_meta)
        para_index = 0

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_meta = {
                        **base_meta,
                        "paragraph_start": para_index,
                    }
            else:
                if current_chunk:
                    chunk_entry = {
                        "content": current_chunk,
                        "metadata": {**current_meta, "paragraph_end": para_index - 1},
                    }
                    chunks_data.append(chunk_entry)

                if len(para) > self.chunk_size:
                    sub_chunks = self._force_split(para, base_meta)
                    chunks_data.extend(sub_chunks)
                    current_chunk = ""
                    current_meta = {**base_meta, "paragraph_start": para_index + 1}
                else:
                    overlap_text = ""
                    if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                        overlap_text = current_chunk[-self.chunk_overlap:]
                    if overlap_text:
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para
                    current_meta = {
                        **base_meta,
                        "paragraph_start": para_index,
                    }

            para_index += 1

        if current_chunk.strip():
            chunk_entry = {
                "content": current_chunk,
                "metadata": {**current_meta, "paragraph_end": para_index - 1},
            }
            chunks_data.append(chunk_entry)

        sent_chunks = self._split_long_sentences(chunks_data)

        for idx, chunk in enumerate(sent_chunks):
            chunk["metadata"]["chunk_index"] = idx

        return sent_chunks

    def _semantic_segments(self, text: str) -> List[str]:
        paragraphs = self._split_paragraphs(text)
        if len(paragraphs) <= 1:
            return [text]

        try:
            from sentence_transformers import SentenceTransformer
            from app.core.config import settings
            import os

            model_name = settings.EMBEDDING_MODEL
            models_dir = os.path.abspath(settings.MODELS_DIR)
            model_slug = model_name.split("/")[-1]
            local_path = os.path.join(models_dir, model_slug)
            if not os.path.isdir(local_path):
                logger.info("[语义分块] 无本地 embedding 模型，跳过语义边界检测")
                return [text]

            model = SentenceTransformer(local_path, local_files_only=True)
            embeddings = model.encode(paragraphs, normalize_embeddings=True, show_progress_bar=False)
            seg_threshold = getattr(settings, 'SEMANTIC_CHUNK_SIMILARITY', 0.6)

            similarities = []
            for i in range(len(embeddings) - 1):
                sim = float(np.dot(embeddings[i], embeddings[i + 1]))
                similarities.append(sim)

            boundaries: List[int] = []
            for i, sim in enumerate(similarities):
                if sim < seg_threshold:
                    boundaries.append(i)
            boundaries.append(len(paragraphs) - 1)

            segments: List[str] = []
            start = 0
            for boundary in boundaries:
                segment = "\n\n".join(paragraphs[start:boundary + 1])
                if segment.strip():
                    segments.append(segment)
                start = boundary + 1

            if len(segments) > 1:
                avg_sim = sum(similarities) / len(similarities) if similarities else 1.0
                logger.info(
                    f"[语义分块] 原文 {len(paragraphs)} 段 → {len(segments)} 个语义区域 "
                    f"(阈值={seg_threshold}, 平均相似度={avg_sim:.3f}, "
                    f"断点={boundaries[:-1] if len(boundaries) > 1 else 'none'})"
                )
            return segments
        except Exception as e:
            logger.warning(f"[语义分块] 失败, 回退到原始文本: {e}")
            return [text]

    def semantic_chunk(self, text: str, metadata: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        base_meta = metadata or {}
        segments = self._semantic_segments(text)

        all_chunks: List[Dict[str, Any]] = []
        for seg_idx, segment in enumerate(segments):
            segment_chunks = self.chunk(segment, base_meta)
            for c in segment_chunks:
                c["metadata"]["semantic_segment"] = seg_idx
            all_chunks.extend(segment_chunks)

        for idx, chunk in enumerate(all_chunks):
            chunk["metadata"]["chunk_index"] = idx

        return all_chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _force_split(self, para: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        sentences = re.split(r"(?<=[。！？.!?])\s*", para)
        current_text = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current_text) + len(sent) + 1 <= self.chunk_size:
                current_text += sent if not current_text else " " + sent
            else:
                if current_text:
                    chunks.append({"content": current_text, "metadata": base_meta.copy()})
                if len(sent) > self.chunk_size:
                    step = self.chunk_size - self.chunk_overlap
                    if step < 1:
                        step = 1
                    for i in range(0, len(sent), step):
                        chunk_text = sent[i:i + self.chunk_size]
                        chunks.append({"content": chunk_text, "metadata": base_meta.copy()})
                    current_text = ""
                else:
                    current_text = sent
        if current_text.strip():
            chunks.append({"content": current_text, "metadata": base_meta.copy()})
        return chunks

    def _split_long_sentences(self, chunks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []

        for chunk in chunks_data:
            content = chunk["content"]
            if len(content) <= self.chunk_size:
                result.append(chunk)
                continue

            sentences = re.split(r"(?<=[。！？.!?])\s*", content)
            sub_chunk = ""
            sub_meta = dict(chunk["metadata"])

            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue

                if len(sub_chunk) + len(sent) + 1 <= self.chunk_size:
                    sub_chunk += sent if not sub_chunk else " " + sent
                else:
                    if sub_chunk:
                        result.append({"content": sub_chunk, "metadata": dict(sub_meta)})
                    if self.chunk_overlap > 0 and len(sub_chunk) > self.chunk_overlap:
                        overlap = sub_chunk[-self.chunk_overlap:]
                        sub_chunk = overlap + " " + sent
                    else:
                        sub_chunk = sent

            if sub_chunk.strip():
                result.append({"content": sub_chunk, "metadata": dict(sub_meta)})

        return result


text_chunker = TextChunker(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
)