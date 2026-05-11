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
from app.services.cross_reranker_service import cross_reranker_service

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))


def _fmt_time(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds*1000000:.0f}us"
    elif seconds < 1:
        return f"{seconds*1000:.0f}ms"
    else:
        return f"{seconds:.3f}s"


def _log_header(title: str) -> None:
    logger.info("")
    logger.info("  \033[1;36m┌── %s\033[0m", title)
    logger.info("  \033[1;36m│\033[0m")


def _log_row(key: str, value: str) -> None:
    logger.info("  \033[1;36m│\033[0m  \033[33m%-10s\033[0m %s", key, value)


def _log_foot(total: float, count: int) -> None:
    logger.info("  \033[1;36m│\033[0m")
    logger.info("  \033[1;36m└──\033[0m total \033[1;32m%s\033[0m  |  \033[1;32m%d results\033[0m", _fmt_time(total), count)
    logger.info("")


def _log_stage(label: str, detail: str) -> None:
    logger.info("  \033[1;36m│\033[0m  \033[1;37m[%s]\033[0m %s", label, detail)


def _log_result_item(rank: int, doc_id: str, title: str, score: float) -> None:
    short_id = doc_id[:8] if len(doc_id) > 8 else doc_id
    short_title = title[:40] if len(title) > 40 else title
    logger.info("  \033[1;36m│\033[0m  \033[1;32m#%-2d\033[0m id=%-10s score=\033[1;33m%.4f\033[0m  %s", rank, short_id, score, short_title)


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
            return f"{title}\n{content}"
        return content

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
            logger.info("  \033[90m[filter] dropped %d below threshold %.2f, kept %d\033[0m",
                       removed_count, threshold, len(filtered))
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
                    c["outdated_warning"] = "该资料入库超过1年，信息可能已过时"
                elif doc_date < six_months_ago:
                    c["is_outdated"] = False
                    c["outdated_warning"] = "该资料入库超过6个月，建议核实最新信息"
                else:
                    c["is_outdated"] = False
                    c["outdated_warning"] = ""
            except (ValueError, TypeError):
                c["is_outdated"] = False
                c["outdated_warning"] = ""

    def _coarse_rank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        bm25_weight: float,
        bge_weight: float,
        query_embedding: List[float],
        coarse_top_k: int,
    ) -> Tuple[List[Dict[str, Any]], List[float], List[float], float]:
        t0 = time.time()

        candidate_texts = [self._format_candidate_text(c) for c in candidates]
        doc_embeddings = embedding_service.encode(candidate_texts)

        bge_similarities = []
        for doc_emb in doc_embeddings:
            sim = self._cosine_similarity(query_embedding, doc_emb)
            bge_similarities.append(sim)

        bge_norm = min_max_normalize(bge_similarities)
        bm25_raw_scores = [c.get("bm25_raw_score", c.get("score", 0.0)) for c in candidates]
        bm25_norm = min_max_normalize(bm25_raw_scores)

        scored: List[Tuple[int, float]] = []
        for i in range(len(candidates)):
            final_score = bm25_weight * bm25_norm[i] + bge_weight * bge_norm[i]
            scored.append((i, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_n = min(coarse_top_k, len(scored))
        coarse_results = [candidates[scored[j][0]] for j in range(top_n)]

        elapsed = time.time() - t0
        return coarse_results, bge_similarities, bm25_raw_scores, elapsed

    def _fine_rank(
        self,
        query: str,
        coarse_results: List[Dict[str, Any]],
    ) -> Tuple[List[Tuple[int, float]], float]:
        t0 = time.time()

        pairs: List[Tuple[str, str]] = []
        for c in coarse_results:
            title = c.get("title", "")
            content = c.get("content", "")
            text = f"{title}\n{content}" if title else content
            pairs.append((title, text))

        scores = cross_reranker_service.compute_scores(query, pairs, normalize=True)

        indexed: List[Tuple[int, float]] = []
        for i, s in enumerate(scores):
            indexed.append((i, float(s)))

        indexed.sort(key=lambda x: x[1], reverse=True)

        elapsed = time.time() - t0
        return indexed, elapsed

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
        coarse_top_k = settings.RERANK_COARSE_TOP_K
        effective_top_k = min(top_k, coarse_top_k)

        _log_header(f"Rerank  |  candidates={len(candidates)}  coarse_top={coarse_top_k}  final_top={effective_top_k}")
        _log_row("query", query[:80])
        _log_row("method", f"coarse: BM25x{bm25_weight} + BGEx{bge_weight}  ->  fine: Cross-Encoder")

        self._mark_temporal_info(candidates)

        before_filter = len(candidates)
        candidates = self.filter_by_threshold(candidates)
        if not candidates:
            logger.info("  \033[1;36m│\033[0m  \033[1;31mALL DROPPED\033[0m - no candidate passed threshold")
            logger.info("")
            return []
        if len(candidates) < before_filter:
            _log_stage("filter", f"{before_filter} -> {len(candidates)} candidates")

        coarse_top_k = min(coarse_top_k, len(candidates))

        if query_embedding is None:
            t_q = time.time()
            query_text = f"{BGE_QUERY_INSTRUCTION}{query}"
            query_embedding = embedding_service.encode_single(query_text)
            _log_stage("embed", f"query vectorized  |  {_fmt_time(time.time() - t_q)}")
        else:
            _log_stage("embed", f"reusing query vector (dim={len(query_embedding)})")

        coarse_results, bge_sims, bm25_scores, coarse_elapsed = self._coarse_rank(
            query=query,
            candidates=candidates,
            bm25_weight=bm25_weight,
            bge_weight=bge_weight,
            query_embedding=query_embedding,
            coarse_top_k=coarse_top_k,
        )

        if bge_sims:
            _log_stage("coarse", f"BGE [{min(bge_sims):.3f}, {max(bge_sims):.3f}]  BM25 [{min(bm25_scores):.3f}, {max(bm25_scores):.3f}]  |  {_fmt_time(coarse_elapsed)}")
        else:
            _log_stage("coarse", f"done  |  {_fmt_time(coarse_elapsed)}")

        _log_stage("coarse", f"top-{len(coarse_results)} selected")

        fine_scores, fine_elapsed = self._fine_rank(query, coarse_results)
        _log_stage("fine", f"cross-encoder {len(fine_scores)} pairs scored  |  {_fmt_time(fine_elapsed)}")

        results: List[Dict[str, Any]] = []
        for rank, (orig_idx, cross_score) in enumerate(fine_scores[:effective_top_k]):
            entry = dict(coarse_results[orig_idx])
            entry["score"] = round(cross_score, 6)
            entry["retriever"] = "rerank"
            results.append(entry)
            _log_result_item(
                rank + 1,
                entry.get("document_id", ""),
                entry.get("title", ""),
                cross_score,
            )

        total_elapsed = time.time() - total_start
        _log_foot(total_elapsed, len(results))

        return results

    def enrich_with_adjacent_chunks(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not results:
            return results

        chunk_requests: List[tuple] = []
        for r in results:
            doc_id = r.get("document_id", "")
            chunk_idx = r.get("chunk_index", 0)
            if doc_id:
                chunk_requests.append((doc_id, chunk_idx))

        if not chunk_requests:
            return results

        filter_parts = []
        for doc_id, chunk_idx in chunk_requests:
            filter_parts.append(
                f'(document_id == "{doc_id}" && (chunk_index == {chunk_idx - 1} || chunk_index == {chunk_idx + 1}))'
            )
        combined_filter = " || ".join(filter_parts)

        try:
            all_neighbors = milvus_service._client.query(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter=combined_filter,
                output_fields=["content", "chunk_index", "document_id"],
                limit=len(chunk_requests) * 2,
            )
        except Exception:
            return results

        neighbor_map: Dict[str, Dict[str, str]] = {}
        for nc in all_neighbors:
            key = f"{nc.get('document_id', '')}_{nc.get('chunk_index', 0)}"
            neighbor_map[key] = nc.get("content", "")

        for r in results:
            doc_id = r.get("document_id", "")
            chunk_idx = r.get("chunk_index", 0)
            if not doc_id:
                continue

            prev_key = f"{doc_id}_{chunk_idx - 1}"
            next_key = f"{doc_id}_{chunk_idx + 1}"

            prev_content = neighbor_map.get(prev_key, "")[:200]
            next_content = neighbor_map.get(next_key, "")[:200]

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

        _log_header(f"RAG Pipeline  |  recall={recall_top_k}  final={top_k}")
        _log_row("query", query[:80])

        t0 = time.time()
        bm25_results = bm25_service.search(query, top_k=recall_top_k)
        bm25_results = self.filter_by_threshold(bm25_results)
        _log_stage("bm25", f"{len(bm25_results)} hits  |  {_fmt_time(time.time() - t0)}")

        t0 = time.time()
        query_for_vector = f"{BGE_QUERY_INSTRUCTION}{query}"
        query_embedding = embedding_service.encode_single(query_for_vector)
        _log_stage("embed", f"query vectorized  |  {_fmt_time(time.time() - t0)}")

        t0 = time.time()
        vector_results = milvus_service.search(query_embedding, top_k=recall_top_k)
        vector_results = self.filter_by_threshold(vector_results)
        _log_stage("vector", f"{len(vector_results)} hits  |  {_fmt_time(time.time() - t0)}")

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

        _log_stage("merge", f"{len(candidates_list)} unique candidates")

        if not candidates_list:
            logger.info("  \033[1;36m│\033[0m  \033[1;31mNO RESULTS\033[0m - both recall paths returned empty")
            logger.info("")
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
        logger.info("  \033[90m↳ pipeline total: %s\033[0m", _fmt_time(total_elapsed))

        return results


reranker_service = RerankerService()
