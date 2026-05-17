import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional

from app.core.config import settings
from app.services.processing.parser import DocumentParser, document_parser
from app.services.processing.text_cleaner import TextCleaner, text_cleaner
from app.services.processing.chunker import TextChunker, text_chunker
from app.services.processing.dedup_service import MinHashDedupService

logger = logging.getLogger(__name__)


@dataclass
class ProcessingPipeline:
    parser: DocumentParser = field(default_factory=lambda: document_parser)
    cleaner: TextCleaner = field(default_factory=lambda: text_cleaner)
    chunker: TextChunker = field(default_factory=lambda: text_chunker)
    dedup_threshold: float = settings.MINHASH_THRESHOLD
    dedup_num_perm: int = settings.MINHASH_NUM_PERM

    def get_supported_types(self) -> set:
        return self.parser.SUPPORTED_TYPES

    def run(
        self,
        file_bytes: bytes | None = None,
        filename: str = "",
        base_metadata: Dict[str, Any] | None = None,
        parsed_text: str | None = None,
        title: str = "",
    ) -> List[Dict[str, Any]]:
        if parsed_text is None:
            if file_bytes is None:
                raise ValueError("必须提供 file_bytes 或 parsed_text")
            parsed_text, title = self.parser.parse(file_bytes, filename)

        if not parsed_text or not parsed_text.strip():
            raise ValueError("文档解析结果为空")

        cleaned_text = self.cleaner.clean(parsed_text)
        if not cleaned_text or not cleaned_text.strip():
            raise ValueError("文本清洗后为空")

        base_meta = base_metadata or {}
        base_meta.setdefault("title", title)
        base_meta.setdefault("source", filename)

        chunks = self.chunker.chunk(cleaned_text, base_meta)
        if not chunks:
            raise ValueError("文本切块结果为空")

        dedup_service = MinHashDedupService(
            threshold=self.dedup_threshold,
            num_perm=self.dedup_num_perm,
        )
        before_dedup = len(chunks)
        chunks = dedup_service.deduplicate(chunks)
        if not chunks:
            raise ValueError("文档内去重后无有效内容，文档可能包含大量重复文本")
        if len(chunks) < before_dedup:
            logger.info(f"[Pipeline] 去重: {before_dedup} → {len(chunks)} chunks")

        return chunks

    @classmethod
    def default(cls) -> "ProcessingPipeline":
        return cls()