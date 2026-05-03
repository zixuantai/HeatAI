import logging
import time
from typing import List, Dict, Any, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class BM25Service:
    _instance = None
    _chunks: List[Dict[str, Any]] = []
    _corpus_texts: List[str] = []
    _tokenized_corpus: List[List[str]] = []
    _bm25 = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        import jieba
        tokens = jieba.lcut(text)
        return [t.strip() for t in tokens if t.strip()]

    def _rebuild_index(self):
        if not self._tokenized_corpus:
            self._bm25 = None
            return
        from rank_bm25 import BM25Okapi
        self._bm25 = BM25Okapi(self._tokenized_corpus)

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return

        for chunk in chunks:
            chunk_id = chunk["metadata"].get("chunk_id", "")
            content = chunk.get("content", "")
            self._chunks.append({
                "id": chunk_id,
                "content": content,
                "document_id": chunk["metadata"].get("document_id", ""),
                "source": chunk["metadata"].get("source", ""),
                "title": chunk["metadata"].get("title", ""),
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
            })
            self._corpus_texts.append(content)
            self._tokenized_corpus.append(self._tokenize(content))

        self._rebuild_index()
        logger.info(f"BM25 索引已更新，当前共 {len(self._chunks)} 条 chunk")

    def remove_by_document_id(self, document_id: str):
        indices_to_keep = [
            i for i, c in enumerate(self._chunks)
            if c["document_id"] != document_id
        ]

        removed = len(self._chunks) - len(indices_to_keep)
        if removed == 0:
            return

        self._chunks = [self._chunks[i] for i in indices_to_keep]
        self._corpus_texts = [self._corpus_texts[i] for i in indices_to_keep]
        self._tokenized_corpus = [self._tokenized_corpus[i] for i in indices_to_keep]

        self._rebuild_index()
        logger.info(f"从 BM25 索引中移除文档 {document_id} 的 {removed} 条 chunk，当前共 {len(self._chunks)} 条")

    def search(self, query: str, top_k: int = 50) -> List[Dict[str, Any]]:
        if self._bm25 is None or not self._chunks:
            return []

        search_start = time.time()
        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        indexed_scores: List[Tuple[int, float]] = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = indexed_scores[:top_k]

        results: List[Dict[str, Any]] = []
        for idx, score in top_indices:
            if score <= 0:
                continue
            chunk = self._chunks[idx]
            results.append({
                "content": chunk["content"],
                "source": chunk["source"],
                "title": chunk["title"],
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "score": float(score),
                "retriever": "bm25",
            })

        elapsed = time.time() - search_start
        logger.info(f"[BM25 检索] 查询词={query}, 召回数={len(results)}, top_k={top_k}, 耗时={elapsed:.4f}s")
        if results:
            logger.info(f"[BM25 检索] 得分详情:")
            for i, r in enumerate(results[:10]):
                logger.info(f"  #{i+1}: doc_id={r['document_id']}, chunk_index={r['chunk_index']}, "
                           f"score={r['score']:.4f}, title={r.get('title', 'N/A')[:40]}")
        else:
            logger.info(f"[BM25 检索] 无相关结果")

        return results

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


bm25_service = BM25Service()
