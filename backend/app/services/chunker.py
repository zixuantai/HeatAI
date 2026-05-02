import re
from typing import List, Dict, Any
from app.core.config import settings


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
                    current_chunk = ""

                if len(para) > self.chunk_size:
                    sub_chunks = self._force_split(para, base_meta)
                    chunks_data.extend(sub_chunks)
                    current_chunk = ""
                    current_meta = {**base_meta, "paragraph_start": para_index + 1}
                elif self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap:]
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

    def _split_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _force_split(self, para: str, base_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        step = self.chunk_size - self.chunk_overlap
        if step < 1:
            step = 1
        for i in range(0, len(para), step):
            chunk_text = para[i:i+self.chunk_size]
            chunks.append({"content": chunk_text, "metadata": base_meta.copy()})
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
