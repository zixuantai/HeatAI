import logging
import time
from typing import List, Dict, Any

from app.core.config import settings
from app.services.bm25_service import bm25_service
from app.services.embedding import embedding_service
from app.services.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _min_max_normalize(scores: List[float]) -> List[float]:
        if not scores:
            return []
        min_s = min(scores)
        max_s = max(scores)
        if max_s == min_s:
            return [1.0] * len(scores)
        return [(s - min_s) / (max_s - min_s) for s in scores]

    @staticmethod
    def _cosine_distance_to_similarity(distances: List[float]) -> List[float]:
        return [max(0.0, 1.0 - d / 2.0) for d in distances]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        total_start = time.time()
        retrieval_top_k = max(top_k * 4, settings.BM25_RETRIEVAL_TOP_K)

        logger.info("=" * 60)
        logger.info(f"[混合检索] 查询: {query}, 最终top_k={top_k}, 召回top_k={retrieval_top_k}")
        logger.info(f"[混合检索] 权重配置: BM25={settings.HYBRID_BM25_WEIGHT}, Vector={settings.HYBRID_VECTOR_WEIGHT}")

        bm25_start = time.time()
        bm25_results = bm25_service.search(query, top_k=retrieval_top_k)
        logger.info(f"[混合检索] BM25 路召回: {len(bm25_results)} 条, 耗时: {time.time() - bm25_start:.4f}s")

        embed_start = time.time()
        query_embedding = embedding_service.encode_single(query)
        embed_time = time.time() - embed_start
        logger.info(f"[混合检索] Query 向量化: dim={len(query_embedding)}, 耗时={embed_time:.4f}s")

        vector_start = time.time()
        vector_results = milvus_service.search(query_embedding, top_k=retrieval_top_k)
        logger.info(f"[混合检索] Vector 路召回: {len(vector_results)} 条, 耗时: {time.time() - vector_start:.4f}s")
        for r in vector_results:
            r["retriever"] = "vector"

        if not bm25_results and not vector_results:
            logger.info(f"[混合检索] 双路均无结果")
            logger.info("=" * 60)
            return []

        bm25_weight = settings.HYBRID_BM25_WEIGHT
        vector_weight = settings.HYBRID_VECTOR_WEIGHT

        chunk_scores: Dict[str, float] = {}
        chunk_data: Dict[str, Dict[str, Any]] = {}

        def chunk_key(result: Dict[str, Any]) -> str:
            return f"{result.get('document_id', '')}_{result.get('chunk_index', 0)}"

        logger.info(f"[混合检索] ---------- 归一化与加权 ----------")

        if bm25_results:
            bm25_scores = [r["score"] for r in bm25_results]
            bm25_norm = self._min_max_normalize(bm25_scores)
            logger.info(f"[混合检索] BM25 原始得分范围: [{min(bm25_scores):.4f}, {max(bm25_scores):.4f}]")
            for i, r in enumerate(bm25_results):
                key = chunk_key(r)
                weighted = bm25_weight * bm25_norm[i]
                chunk_scores[key] = chunk_scores.get(key, 0.0) + weighted
                if key not in chunk_data:
                    chunk_data[key] = r
                if i < 5:
                    logger.info(f"  BM25 #{i+1}: key={key}, raw={bm25_scores[i]:.4f}, "
                               f"norm={bm25_norm[i]:.4f}, weighted={weighted:.4f}")

        if vector_results:
            vector_scores_raw = [r["score"] for r in vector_results]
            vector_similarities = self._cosine_distance_to_similarity(vector_scores_raw)
            vector_norm = self._min_max_normalize(vector_similarities)
            logger.info(f"[混合检索] Vector 原始距离范围: [{min(vector_scores_raw):.6f}, {max(vector_scores_raw):.6f}]")
            logger.info(f"[混合检索] Vector 相似度范围: [{min(vector_similarities):.4f}, {max(vector_similarities):.4f}]")
            for i, r in enumerate(vector_results):
                key = chunk_key(r)
                weighted = vector_weight * vector_norm[i]
                chunk_scores[key] = chunk_scores.get(key, 0.0) + weighted
                if key not in chunk_data:
                    chunk_data[key] = r
                if i < 5:
                    logger.info(f"  Vector #{i+1}: key={key}, raw_dist={vector_scores_raw[i]:.6f}, "
                               f"sim={vector_similarities[i]:.4f}, norm={vector_norm[i]:.4f}, weighted={weighted:.4f}")

        sorted_keys = sorted(chunk_scores.keys(), key=lambda k: chunk_scores[k], reverse=True)
        top_keys = sorted_keys[:top_k]

        logger.info(f"[混合检索] ---------- 融合排名 ----------")
        logger.info(f"[混合检索] 融合后唯一文档块数: {len(sorted_keys)}, 召回路数: BM25={bm25_weight}, Vector={vector_weight}")

        results: List[Dict[str, Any]] = []
        for rank, key in enumerate(top_keys):
            entry = dict(chunk_data[key])
            fusion_score = round(chunk_scores[key], 6)
            entry["score"] = fusion_score
            entry["retriever"] = "hybrid"
            results.append(entry)
            logger.info(f"  排名 #{rank+1}: doc_id={entry.get('document_id', 'N/A')}, "
                       f"chunk_index={entry.get('chunk_index', 'N/A')}, "
                       f"fusion_score={fusion_score:.6f}, "
                       f"title={entry.get('title', 'N/A')[:50]}")

        total_elapsed = time.time() - total_start
        logger.info(f"[混合检索] ✅ 最终返回: {len(results)} 条, 总耗时={total_elapsed:.4f}s")
        logger.info("=" * 60)

        return results


hybrid_service = HybridRetrievalService()
