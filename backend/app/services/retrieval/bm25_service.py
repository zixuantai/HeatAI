import logging
import os
import threading
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class _OrgIndex:
    __slots__ = ("searcher", "corpus_chunks", "tokenized_corpus", "chunk_ids", "org_id", "knowledge_base_id")

    def __init__(self, org_id: str = "", knowledge_base_id: str = ""):
        self.searcher = None
        self.corpus_chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.chunk_ids: List[str] = []
        self.org_id = org_id
        self.knowledge_base_id = knowledge_base_id


class BM25Service:
    _instance = None
    _lock = threading.Lock()
    _dict_loaded = False
    _indexes: Dict[str, _OrgIndex] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _lazy_import_jieba(self):
        import jieba
        if not self.__class__._dict_loaded:
            self._load_thermal_dict()
            self.__class__._dict_loaded = True
        return jieba

    def _get_jieba(self):
        try:
            import jieba
            return jieba.dt
        except ImportError:
            return None

    def _load_thermal_dict(self):
        import jieba
        dict_path = os.path.join(settings.JIEBA_DICT_DIR, "thermal_terms.txt")
        if os.path.isfile(dict_path):
            try:
                count = 0
                with open(dict_path, "r", encoding="utf-8") as f:
                    for line in f:
                        term = line.strip()
                        if term:
                            jieba.add_word(term, freq=100, tag="n")
                            count += 1
                logger.info(f"jieba 供热行业词典已加载: {count} 个术语 ({dict_path})")
            except Exception as e:
                logger.warning(f"加载 jieba 词典失败: {e}")
        else:
            logger.info(f"jieba 供热行业词典不存在: {dict_path}, 跳过")

    def _tokenize(self, text: str) -> List[str]:
        jieba = self._lazy_import_jieba()
        tokens = jieba.lcut(text)
        return [t for t in tokens if t.strip()]

    @staticmethod
    def _get_org_key(org_id: str | None, knowledge_base_id: str | None = None) -> str:
        if knowledge_base_id:
            return f"kb:{knowledge_base_id}"
        return f"org:{org_id or ''}"

    def _get_index(self, org_id: str | None = None, knowledge_base_id: str | None = None) -> _OrgIndex:
        key = self._get_org_key(org_id, knowledge_base_id)
        if key not in self._indexes:
            self._indexes[key] = _OrgIndex(org_id=org_id or "", knowledge_base_id=knowledge_base_id or "")
        return self._indexes[key]

    def _build_index_for_org(self, idx: _OrgIndex):
        from rank_bm25 import BM25Okapi

        if not idx.corpus_chunks:
            idx.searcher = None
            idx.tokenized_corpus = []
            idx.chunk_ids = []
            return

        idx.chunk_ids = [c.get("id", str(i)) for i, c in enumerate(idx.corpus_chunks)]

        tokenized_corpus = []
        for c in idx.corpus_chunks:
            content = c.get("content", "")
            tokens = self._tokenize(content)
            tokenized_corpus.append(tokens)

        idx.tokenized_corpus = tokenized_corpus
        idx.searcher = BM25Okapi(tokenized_corpus)

    @property
    def chunk_count(self) -> int:
        return sum(len(idx.corpus_chunks) for idx in self._indexes.values())

    def rebuild_from_milvus_chunks(self, chunks: List[Dict[str, Any]]):
        from collections import defaultdict
        org_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            kb_id = meta.get("knowledge_base_id", "")
            org_id = meta.get("organization_id", "")
            key = self._get_org_key(org_id, kb_id or None)
            org_groups[key].append(chunk)

        if not org_groups:
            self.build_index([], "")
            return

        for key, group_chunks in org_groups.items():
            idx = _OrgIndex()
            idx.corpus_chunks = group_chunks
            self._build_index_for_org(idx)
            self._indexes[key] = idx
            logger.info(f"BM25 索引已构建: key={key}, chunks={len(group_chunks)}")

    def build_index(self, chunks: List[Dict[str, Any]], org_id: str | None = None, knowledge_base_id: str | None = None):
        idx = self._get_index(org_id, knowledge_base_id)

        if not chunks:
            idx.searcher = None
            idx.corpus_chunks = []
            idx.tokenized_corpus = []
            idx.chunk_ids = []
            return

        idx.corpus_chunks = chunks
        self._build_index_for_org(idx)
        label = knowledge_base_id or org_id or "(global)"
        logger.info(f"BM25 index built: key={label}, {len(chunks)} documents")

    def ensure_index(self, org_id: str | None = None, knowledge_base_id: str | None = None):
        idx = self._get_index(org_id, knowledge_base_id)
        if idx.searcher is not None:
            return
        with self._lock:
            if idx.searcher is not None:
                return
            from app.services.retrieval.milvus_service import milvus_service
            all_chunks = milvus_service.get_all_chunks()
            if knowledge_base_id:
                chunks = [c for c in all_chunks if c.get("knowledge_base_id") == knowledge_base_id]
            elif org_id:
                chunks = [c for c in all_chunks if c.get("organization_id") == org_id]
            else:
                chunks = [c for c in all_chunks if not c.get("organization_id")]
            if chunks:
                self.build_index(chunks, org_id, knowledge_base_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        org_id: str | None = None,
        document_ids: List[str] | None = None,
        knowledge_base_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        idx = self._get_index(org_id, knowledge_base_id)
        if not idx.searcher:
            if knowledge_base_id and document_ids:
                idx = self._get_index(org_id)
                if not idx.searcher:
                    return []
            else:
                return []

        query_tokens = self._tokenize(query)
        scores = idx.searcher.get_scores(query_tokens)

        doc_id_set = set(document_ids) if document_ids is not None else None
        indexed = [(i, float(s)) for i, s in enumerate(scores) if s > 0]
        indexed.sort(key=lambda x: x[1], reverse=True)

        results: List[Dict[str, Any]] = []
        for i, score in indexed:
            if len(results) >= top_k:
                break
            chunk = idx.corpus_chunks[i]
            if doc_id_set is not None and chunk.get("document_id", "") not in doc_id_set:
                continue
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

    def add_chunks(self, chunks: List[Dict[str, Any]], org_id: str | None = None, knowledge_base_id: str | None = None):
        if not chunks:
            return
        idx = self._get_index(org_id, knowledge_base_id)

        flat_chunks = []
        for c in chunks:
            meta = c.get("metadata", {})
            flat = {
                "content": c.get("content", ""),
                "id": meta.get("chunk_id", meta.get("id", "")),
                "source": meta.get("source", ""),
                "title": meta.get("title", ""),
                "document_id": meta.get("document_id", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "created_at": meta.get("created_at", ""),
                "version": meta.get("version", 1),
                "knowledge_base_id": knowledge_base_id or "",
            }
            flat_chunks.append(flat)
        idx.corpus_chunks.extend(flat_chunks)
        self._build_index_for_org(idx)
        label = knowledge_base_id or org_id or "(global)"
        logger.info(f"BM25 index: added {len(chunks)} chunks to key={label}, total: {len(idx.corpus_chunks)}")

    def remove_by_document_id(self, document_id: str, org_id: str | None = None, knowledge_base_id: str | None = None):
        self.delete_document_index(document_id, org_id, knowledge_base_id)

    def remove_by_document_ids(self, document_ids: list[str], org_id: str | None = None, knowledge_base_id: str | None = None):
        if not document_ids:
            return
        idx = self._get_index(org_id, knowledge_base_id)
        if not idx.corpus_chunks:
            return

        ids_set = set(document_ids)
        before = len(idx.corpus_chunks)
        idx.corpus_chunks = [c for c in idx.corpus_chunks if c.get("document_id") not in ids_set]
        idx.chunk_ids = [c.get("id", str(i)) for i, c in enumerate(idx.corpus_chunks)]
        if idx.corpus_chunks:
            self._build_index_for_org(idx)
        else:
            idx.searcher = None
            idx.tokenized_corpus = []
        after = len(idx.corpus_chunks)
        logger.info(f"BM25 index: removed {before - after} chunks for {len(document_ids)} documents")

    def delete_document_index(self, document_id: str, org_id: str | None = None, knowledge_base_id: str | None = None):
        idx = self._get_index(org_id, knowledge_base_id)
        if not idx.corpus_chunks:
            return

        before = len(idx.corpus_chunks)
        idx.corpus_chunks = [c for c in idx.corpus_chunks if c.get("document_id") != document_id]
        idx.chunk_ids = [c.get("id", str(i)) for i, c in enumerate(idx.corpus_chunks)]
        if idx.corpus_chunks:
            self._build_index_for_org(idx)
        else:
            idx.searcher = None
            idx.tokenized_corpus = []
        after = len(idx.corpus_chunks)
        logger.info(f"BM25 index: removed {before - after} chunks for document {document_id}")


bm25_service = BM25Service()
