import logging
import os
import threading
from typing import List, Dict, Any
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class BM25Service:
    _instance = None
    _searcher = None
    _corpus_chunks: List[Dict[str, Any]] = []
    _chunk_ids: List[str] = []
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _lazy_import_jieba(self):
        import jieba
        return jieba

    def _get_jieba(self):
        try:
            import jieba
            return jieba.dt
        except ImportError:
            return None

    def _tokenize(self, text: str) -> List[str]:
        jieba = self._lazy_import_jieba()
        tokens = jieba.lcut(text)
        return [t for t in tokens if t.strip()]

    @property
    def chunk_count(self) -> int:
        return len(self._corpus_chunks)

    def rebuild_from_milvus_chunks(self, chunks: List[Dict[str, Any]]):
        self.build_index(chunks)

    def build_index(self, chunks: List[Dict[str, Any]]):
        from rank_bm25 import BM25Okapi

        if not chunks:
            self._searcher = None
            self._corpus_chunks = []
            self._chunk_ids = []
            return

        self._corpus_chunks = chunks
        self._chunk_ids = [c.get("id", str(i)) for i, c in enumerate(chunks)]

        tokenized_corpus = []
        for c in chunks:
            content = c.get("content", "")
            tokens = self._tokenize(content)
            tokenized_corpus.append(tokens)

        self._searcher = BM25Okapi(tokenized_corpus)
        logger.info(f"BM25 index built with {len(chunks)} documents")

    def ensure_index(self):
        if self._searcher is not None:
            return
        with self._lock:
            if self._searcher is not None:
                return
            from app.services.retrieval.milvus_service import milvus_service
            chunks = milvus_service.get_all_chunks()
            if chunks:
                self.build_index(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not self._searcher:
            return []

        query_tokens = self._tokenize(query)
        scores = self._searcher.get_scores(query_tokens)

        indexed = [(i, float(s)) for i, s in enumerate(scores) if s > 0]
        indexed.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for idx, score in indexed[:top_k]:
            chunk = self._corpus_chunks[idx]
            results.append({
                "content": chunk.get("content", ""),
                "source": chunk.get("source", ""),
                "title": chunk.get("title", ""),
                "document_id": chunk.get("document_id", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "score": round(score, 6),
                "created_at": chunk.get("created_at", ""),
                "version": chunk.get("version", 1),
            })

        return results

    def delete_document_index(self, document_id: str):
        if not self._corpus_chunks:
            return
        before = len(self._corpus_chunks)
        self._corpus_chunks = [c for c in self._corpus_chunks if c.get("document_id") != document_id]
        self._chunk_ids = [c.get("id", str(i)) for i, c in enumerate(self._corpus_chunks)]
        if self._corpus_chunks:
            self.build_index(self._corpus_chunks)
        else:
            self._searcher = None
        after = len(self._corpus_chunks)
        logger.info(f"BM25 index: removed {before - after} chunks for document {document_id}")


bm25_service = BM25Service()