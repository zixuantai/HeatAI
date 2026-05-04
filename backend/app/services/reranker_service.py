import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

import numpy as np

from app.core.config import settings
from app.core.utils import min_max_normalize
from app.services.bm25_service import bm25_service
from app.services.embedding import embedding_service, BGE_QUERY_INSTRUCTION
from app.services.milvus_service import milvus_service

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))


class RerankerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _chunk_key(result: Dict[str, Any]) -> str:
        return f"{result.get('document_id', '')}_{result.get('chunk_index', 0)}"

    @staticmethod
    def _format_candidate_text(candidate: Dict[str, Any]) -> str:
        title = candidate.get("title", "")
        content = candidate.get("content", "")
        if title:
            return f"文档标题：{title}\n文档摘要：{content}"
        return f"文档摘要：{content}"

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        a = np.array(vec1)
        b = np.array(vec2)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        sim = dot / (norm_a * norm_b)
        return max(0.0, min(1.0, float(sim)))

    @staticmethod
    def _cosine_similarity_from_distance(distance: float) -> float:
        return max(0.0, 1.0 - float(distance))

    @staticmethod
    def filter_by_threshold(
        candidates: List[Dict[str, Any]],
        threshold: float | None = None,
    ) -> List[Dict[str, Any]]:
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD
        if threshold <= 0:
            return candidates

        filtered: List[Dict[str, Any]] = []
        removed_count = 0
        for c in candidates:
            raw_score = c.get("score", 0)
            similarity = RerankerService._cosine_similarity_from_distance(raw_score)
            if similarity >= threshold:
                filtered.append(c)
            else:
                removed_count += 1

        if removed_count > 0:
            logger.info(f"[阈值过滤] 移除 {removed_count} 条低相关度结果 (阈值={threshold}), 保留 {len(filtered)} 条")
        return filtered

    @staticmethod
    def _mark_temporal_info(candidates: List[Dict[str, Any]]) -> None:
        now = datetime.now(CST)
        six_months_ago = now - timedelta(days=180)
        one_year_ago = now - timedelta(days=365)

        for c in candidates:
            created_at = c.get("created_at", "")
            if not created_at:
                c["is_outdated"] = False
                c["outdated_warning"] = ""
                continue

            try:
                dt_str = created_at[:19]
                doc_date = datetime.fromisoformat(dt_str)
                if doc_date < one_year_ago:
                    c["is_outdated"] = True
                    c["outdated_warning"] = "⚠️ 该资料入库超过1年，信息可能已过时"
                elif doc_date < six_months_ago:
                    c["is_outdated"] = False
                    c["outdated_warning"] = "该资料入库超过6个月，建议核实最新信息"
                else:
                    c["is_outdated"] = False
                    c["outdated_warning"] = ""
            except (ValueError, TypeError):
                c["is_outdated"] = False
                c["outdated_warning"] = ""

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        bm25_weight: float | None = None,
        bge_weight: float | None = None,
        query_embedding: List[float] | None = None,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        if bm25_weight is None:
            bm25_weight = settings.RERANK_BM25_WEIGHT
        if bge_weight is None:
            bge_weight = settings.RERANK_BGE_WEIGHT

        total_start = time.time()
        logger.info("=" * 60)
        logger.info(f"[重排序] 查询: {query}, 候选数={len(candidates)}, top_k={top_k}")
        logger.info(f"[重排序] 权重: BM25={bm25_weight}, BGE={bge_weight}")

        self._mark_temporal_info(candidates)
        candidates = self.filter_by_threshold(candidates)
        if not candidates:
            logger.info(f"[重排序] 所有候选均未达到相似度阈值，无结果返回")
            logger.info("=" * 60)
            return []

        if query_embedding is not None:
            logger.info(f"[重排序] 复用传入的查询向量 (dim={len(query_embedding)})，跳过重复编码")
        else:
            embed_start = time.time()
            query_text = f"{BGE_QUERY_INSTRUCTION}{query}"
            query_embedding = embedding_service.encode_single(query_text)
            logger.info(f"[重排序] 查询向量化 耗时: {time.time() - embed_start:.4f}s")

        candidate_texts = [self._format_candidate_text(c) for c in candidates]
        doc_embed_start = time.time()
        doc_embeddings = embedding_service.encode(candidate_texts)
        logger.info(f"[重排序] 文档向量化 ({len(candidate_texts)}条) 耗时: {time.time() - doc_embed_start:.4f}s")

        sim_start = time.time()
        bge_similarities = []
        for doc_emb in doc_embeddings:
            sim = self._cosine_similarity(query_embedding, doc_emb)
            bge_similarities.append(sim)
        logger.info(f"[重排序] 余弦相似度计算 耗时: {time.time() - sim_start:.4f}s")

        bge_norm = min_max_normalize(bge_similarities)
        bm25_raw_scores = [c.get("bm25_raw_score", c.get("score", 0.0)) for c in candidates]
        bm25_norm = min_max_normalize(bm25_raw_scores)

        if bge_similarities:
            logger.info(f"[重排序] BGE 相似度范围: [{min(bge_similarities):.4f}, {max(bge_similarities):.4f}]")
        if bm25_raw_scores:
            logger.info(f"[重排序] BM25 原始得分范围: [{min(bm25_raw_scores):.4f}, {max(bm25_raw_scores):.4f}]")

        scored: List[Tuple[int, float, Dict[str, Any]]] = []
        for i, candidate in enumerate(candidates):
            final_score = bm25_weight * bm25_norm[i] + bge_weight * bge_norm[i]
            scored.append((i, final_score, candidate))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_scored = scored[:top_k]

        results: List[Dict[str, Any]] = []
        for rank, (orig_idx, final_score, candidate) in enumerate(top_scored):
            entry = dict(candidate)
            entry["score"] = round(final_score, 6)
            entry["bge_similarity"] = round(bge_similarities[orig_idx], 6)
            entry["bm25_raw_score"] = round(bm25_raw_scores[orig_idx], 6)
            entry["retriever"] = "rerank"
            results.append(entry)
            logger.info(f"  排名 #{rank+1}: doc_id={entry.get('document_id', 'N/A')}, "
                       f"title={entry.get('title', 'N/A')[:50]}, "
                       f"final_score={final_score:.6f}, "
                       f"bge_sim={bge_similarities[orig_idx]:.4f}, "
                       f"bm25_raw={bm25_raw_scores[orig_idx]:.4f}")

        total_elapsed = time.time() - total_start
        logger.info(f"[重排序] ✅ 最终返回: {len(results)} 条, 总耗时={total_elapsed:.4f}s")
        logger.info("=" * 60)

        return results

    def enrich_with_adjacent_chunks(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not results:
            return results

        for r in results:
            doc_id = r.get("document_id", "")
            chunk_idx = r.get("chunk_index", 0)
            if not doc_id:
                continue

            try:
                expr = f'document_id == "{doc_id}" && (chunk_index == {chunk_idx - 1} || chunk_index == {chunk_idx + 1})'
                neighbor_chunks = milvus_service._client.query(
                    collection_name=settings.MILVUS_COLLECTION_NAME,
                    filter=expr,
                    output_fields=["content", "chunk_index"],
                    limit=2,
                )
            except Exception:
                continue

            prev_content = ""
            next_content = ""
            for nc in neighbor_chunks:
                if nc.get("chunk_index") == chunk_idx - 1:
                    prev_content = nc.get("content", "")[:200]
                elif nc.get("chunk_index") == chunk_idx + 1:
                    next_content = nc.get("content", "")[:200]

            if prev_content:
                r["adjacent_prev"] = prev_content
            if next_content:
                r["adjacent_next"] = next_content

        return results

    def search_and_rerank(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float | None = None,
        bge_weight: float | None = None,
    ) -> List[Dict[str, Any]]:
        total_start = time.time()
        recall_top_k = settings.RERANK_RECALL_TOP_K

        logger.info("=" * 60)
        logger.info(f"[重排序检索] 查询: {query}, 最终top_k={top_k}, 召回top_k={recall_top_k}")

        bm25_start = time.time()
        bm25_results = bm25_service.search(query, top_k=recall_top_k)
        bm25_results = self.filter_by_threshold(bm25_results)
        logger.info(f"[重排序检索] BM25 召回: {len(bm25_results)} 条, 耗时: {time.time() - bm25_start:.4f}s")

        embed_start = time.time()
        query_for_vector = f"{BGE_QUERY_INSTRUCTION}{query}"
        query_embedding = embedding_service.encode_single(query_for_vector)
        logger.info(f"[重排序检索] 查询向量化 耗时: {time.time() - embed_start:.4f}s")

        vector_start = time.time()
        vector_results = milvus_service.search(query_embedding, top_k=recall_top_k)
        vector_results = self.filter_by_threshold(vector_results)
        logger.info(f"[重排序检索] Vector 召回: {len(vector_results)} 条, 耗时: {time.time() - vector_start:.4f}s")

        bm25_score_map: Dict[str, float] = {}
        for r in bm25_results:
            key = self._chunk_key(r)
            bm25_score_map[key] = r["score"]

        all_candidates: Dict[str, Dict[str, Any]] = {}
        for r in bm25_results:
            key = self._chunk_key(r)
            if key not in all_candidates:
                all_candidates[key] = r

        for r in vector_results:
            key = self._chunk_key(r)
            if key not in all_candidates:
                all_candidates[key] = r

        candidates_list = list(all_candidates.values())
        for c in candidates_list:
            key = self._chunk_key(c)
            c["bm25_raw_score"] = bm25_score_map.get(key, 0.0)

        logger.info(f"[重排序检索] 合并去重后候选数: {len(candidates_list)}")

        if not candidates_list:
            logger.info(f"[重排序检索] 双路均无结果")
            logger.info("=" * 60)
            return []

        results = self.rerank(
            query=query,
            candidates=candidates_list,
            top_k=top_k,
            bm25_weight=bm25_weight,
            bge_weight=bge_weight,
            query_embedding=query_embedding,
        )

        results = self.enrich_with_adjacent_chunks(results)

        total_elapsed = time.time() - total_start
        logger.info(f"[重排序检索] ✅ 全部完成, 总耗时={total_elapsed:.4f}s")
        logger.info("=" * 60)

        return results


reranker_service = RerankerService()
