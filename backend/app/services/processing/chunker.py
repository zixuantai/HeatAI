import re
from typing import List, Dict, Any
from app.core.config import settings

_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？.!?；;])\s*")
_NATURAL_BREAKS_RE = re.compile(r"[\s,，、；;。！？.!?：:]")


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
                    if self.chunk_overlap > 0 and len(current_chunk) >= self.chunk_overlap:
                        overlap_text = current_chunk[-self.chunk_overlap:]
                    else:
                        overlap_text = current_chunk
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
            chunk["metadata"]["chunk_count"] = len(sent_chunks)

        char_pos = 0
        for chunk in sent_chunks:
            content = chunk["content"]
            pos = text.find(content, char_pos)
            if pos >= 0:
                chunk["metadata"]["char_offset"] = pos
                chunk["metadata"]["char_length"] = len(content)
                char_pos = pos + len(content)
            else:
                chunk["metadata"]["char_offset"] = char_pos
                chunk["metadata"]["char_length"] = len(content)

        return sent_chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _find_safe_cut(self, text: str, max_len: int) -> int:
        if len(text) <= max_len:
            return len(text)
        for i in range(max_len, max(0, max_len - 60), -1):
            if _NATURAL_BREAKS_RE.match(text[i]):
                return i + 1
        return max_len

    def _force_split(self, para: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        sentences = _SENTENCE_BOUNDARY_RE.split(para)
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
                    pos = 0
                    while pos < len(sent):
                        end = self._find_safe_cut(sent, pos + self.chunk_size)
                        chunk_text = sent[pos:end]
                        if chunk_text:
                            chunks.append({"content": chunk_text, "metadata": base_meta.copy()})
                        pos = max(pos + step, end - self.chunk_overlap if end - self.chunk_overlap > pos else pos + 1)
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

            sentences = _SENTENCE_BOUNDARY_RE.split(content)
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
                    overlap_len = min(self.chunk_overlap, len(sub_chunk))
                    if overlap_len > 0:
                        sub_chunk = sub_chunk[-overlap_len:] + " " + sent
                    else:
                        sub_chunk = sent

            if sub_chunk.strip():
                result.append({"content": sub_chunk, "metadata": dict(sub_meta)})

        return result


text_chunker = TextChunker(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
)