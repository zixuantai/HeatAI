"""
RAG 流水线桥梁函数

将 eval 评估系统与 HeatAI 后端真实的 RAG 流水线对接。
评估系统每问一条问题，就调用 bridge 函数获取真实的 answer + contexts，
然后用 Ragas / 传统 IR 指标进行打分。

核心流水线:
    question → query_rewriter.rewrite() → swap → search_and_rerank() 
    → merge_expanded_results() → chat_service.ask() → {answer, contexts}

同步封装：内部使用 asyncio.run() 桥接异步后端函数。
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Callable

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_backend_dir = _project_root / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

os.environ.setdefault("HF_HUB_CACHE", str(_project_root / "models"))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(_project_root / "models"))

for _env_path in [
    _project_root / "backend" / ".env",
    _project_root / ".env",
    Path(__file__).parent / ".env",
]:
    if _env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_path, override=False)
        except ImportError:
            pass

from backend.app.core.config import settings
from backend.app.services.retrieval.reranker_service import reranker_service
from backend.app.services.retrieval.embedding import embedding_service, BGE_QUERY_INSTRUCTION
from backend.app.services.retrieval.bm25_service import bm25_service
from backend.app.services.retrieval.milvus_service import milvus_service

logger = logging.getLogger(__name__)


def _ensure_models_loaded():
    embedding_service.ensure_loaded()
    from backend.app.services.retrieval.cross_reranker_service import cross_reranker_service
    cross_reranker_service.ensure_loaded()


async def _rewrite_query(question: str) -> dict:
    from backend.app.services.chat.engine.query_rewriter import query_rewriter

    skip = query_rewriter.should_skip_rewrite(question)
    if skip:
        return {
            "original_query": question,
            "rewritten_query": question,
            "expanded_queries": [],
        }
    return await query_rewriter.rewrite(question)


async def _merge_expanded_results(main_results: list, rewrite_result: dict) -> list:
    expanded_queries = rewrite_result.get("expanded_queries", [])
    if not expanded_queries:
        return main_results

    seen_keys = set()
    for r in main_results:
        key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
        seen_keys.add(key)

    threshold = settings.SIMILARITY_THRESHOLD

    async def _search_one(eq: str):
        try:
            bm25_res = await asyncio.to_thread(bm25_service.search, eq, 3)
            bm25_res = reranker_service.filter_by_threshold(bm25_res, threshold)
            query_emb = await asyncio.to_thread(
                embedding_service.encode_single, BGE_QUERY_INSTRUCTION + eq
            )
            vector_res = await asyncio.to_thread(milvus_service.search, query_emb, 3)
            vector_res = reranker_service.filter_by_threshold(vector_res, threshold)
            for r in vector_res:
                r["retriever"] = "vector_expanded"
            merged = list(bm25_res)
            bm25_keys = {f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}" for r in bm25_res}
            for r in vector_res:
                key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
                if key not in bm25_keys:
                    merged.append(r)
            return merged
        except Exception:
            return []

    all_expanded = await asyncio.gather(*[_search_one(eq) for eq in expanded_queries])

    merged = list(main_results)
    for exp_results in all_expanded:
        for r in exp_results:
            key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
            if key not in seen_keys:
                seen_keys.add(key)
                if "retriever" not in r:
                    r["retriever"] = "bm25_expanded"
                merged.append(r)

    return merged


async def _run_full_pipeline(
    question: str,
    enable_rewrite: bool = True,
    enable_bm25: bool = True,
    enable_fine_rank: bool = True,
    enable_context_enrich: bool = True,
) -> dict:
    from backend.app.services.chat.service import chat_service

    if enable_rewrite:
        rewrite_result = await _rewrite_query(question)
    else:
        rewrite_result = {
            "original_query": question,
            "rewritten_query": question,
            "expanded_queries": [],
        }

    search_query = rewrite_result["rewritten_query"]

    if enable_bm25 and enable_fine_rank:
        search_results = await asyncio.to_thread(
            reranker_service.search_and_rerank, search_query
        )
    elif enable_bm25 and not enable_fine_rank:
        search_results = await _search_bm25_vector_coarse_only(search_query)
    elif not enable_bm25:
        search_results = await _search_vector_only(search_query, enable_fine_rank=enable_fine_rank)

    if enable_context_enrich:
        pass
    else:
        for r in (search_results or []):
            r.pop("adjacent_prev", None)
            r.pop("adjacent_next", None)

    if enable_rewrite and rewrite_result.get("expanded_queries"):
        search_results = await _merge_expanded_results(search_results, rewrite_result)

    result = await chat_service.ask(question, history=None, search_results=search_results or [])

    contexts = [r.get("content", "") for r in (search_results or [])]
    context_ids = [r.get("document_id", "") for r in (search_results or [])]
    context_scores = [r.get("score", 0.0) for r in (search_results or [])]

    return {
        "answer": result.get("answer", ""),
        "contexts": contexts,
        "context_ids": context_ids,
        "context_scores": context_scores,
        "metadata": {
            "search_count": len(search_results or []),
            "rewritten_query": rewrite_result.get("rewritten_query", question),
            "expanded_queries": rewrite_result.get("expanded_queries", []),
            "model": result.get("model", ""),
            "tool_calls": result.get("tool_calls", []),
        },
    }


async def _search_vector_only(query: str, enable_fine_rank: bool = True) -> list:
    query_for_vector = f"{BGE_QUERY_INSTRUCTION}{query}"
    query_embedding = embedding_service.encode_single(query_for_vector)
    vector_results = milvus_service.search(query_embedding, top_k=settings.RERANK_RECALL_TOP_K)
    vector_results = reranker_service.filter_by_threshold(vector_results)

    candidates = vector_results
    if not candidates:
        return []

    self = reranker_service
    top_k = settings.RERANK_FINAL_TOP_K
    coarse_top_k = min(settings.RERANK_COARSE_TOP_K, len(candidates))

    self._mark_temporal_info(candidates)

    coarse_results, _, _, _ = self._coarse_rank(
        query=query,
        candidates=candidates,
        bm25_weight=0.0,
        bge_weight=1.0,
        query_embedding=query_embedding,
        coarse_top_k=coarse_top_k,
    )

    if enable_fine_rank:
        fine_scores, _ = self._fine_rank(query, coarse_results)
        effective_top_k = min(top_k, len(fine_scores))
        results = []
        for rank, (orig_idx, cross_score) in enumerate(fine_scores[:effective_top_k]):
            entry = dict(coarse_results[orig_idx])
            entry["score"] = round(cross_score, 6)
            entry["retriever"] = "rerank_vector_only"
            results.append(entry)
    else:
        effective_top_k = min(top_k, len(coarse_results))
        results = list(coarse_results[:effective_top_k])
        for r in results:
            r["retriever"] = r.get("retriever", "coarse_vector_only")

    results = self.enrich_with_adjacent_chunks(results)
    return results


async def _search_bm25_vector_coarse_only(search_query: str) -> list:
    bm25_results = await asyncio.to_thread(
        bm25_service.search, search_query, settings.RERANK_RECALL_TOP_K
    )
    bm25_results = reranker_service.filter_by_threshold(bm25_results)

    query_for_vector = f"{BGE_QUERY_INSTRUCTION}{search_query}"
    query_embedding = await asyncio.to_thread(
        embedding_service.encode_single, query_for_vector
    )
    vector_results = await asyncio.to_thread(
        milvus_service.search, query_embedding, settings.RERANK_RECALL_TOP_K
    )
    vector_results = reranker_service.filter_by_threshold(vector_results)

    seen_keys = set()
    candidates = []
    for r in bm25_results:
        key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
        seen_keys.add(key)
        candidates.append(r)
    for r in vector_results:
        key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
        if key not in seen_keys:
            seen_keys.add(key)
            candidates.append(r)

    if not candidates:
        return []

    self = reranker_service
    top_k = settings.RERANK_FINAL_TOP_K
    coarse_top_k = min(settings.RERANK_COARSE_TOP_K, len(candidates))

    self._mark_temporal_info(candidates)

    coarse_results, _, _, _ = self._coarse_rank(
        query=search_query,
        candidates=candidates,
        bm25_weight=settings.RERANK_COARSE_BM25_WEIGHT,
        bge_weight=settings.RERANK_COARSE_BGE_WEIGHT,
        query_embedding=query_embedding,
        coarse_top_k=coarse_top_k,
    )

    effective_top_k = min(top_k, len(coarse_results))
    results = list(coarse_results[:effective_top_k])
    for r in results:
        r["retriever"] = r.get("retriever", "coarse_bm25_vector")

    return results


def full_pipeline_fn(question: str) -> dict:
    _ensure_models_loaded()
    return asyncio.run(_run_full_pipeline(question))


def no_rewrite_pipeline_fn(question: str) -> dict:
    _ensure_models_loaded()
    return asyncio.run(_run_full_pipeline(question, enable_rewrite=False))


def no_bm25_pipeline_fn(question: str) -> dict:
    _ensure_models_loaded()
    return asyncio.run(_run_full_pipeline(question, enable_bm25=False))


def no_fine_rank_pipeline_fn(question: str) -> dict:
    _ensure_models_loaded()
    return asyncio.run(_run_full_pipeline(question, enable_fine_rank=False))


def no_context_enrich_pipeline_fn(question: str) -> dict:
    _ensure_models_loaded()
    return asyncio.run(_run_full_pipeline(question, enable_context_enrich=False))


ABLATION_PIPELINES: dict[str, Callable] = {
    "no_rewrite": no_rewrite_pipeline_fn,
    "no_bm25": no_bm25_pipeline_fn,
    "no_fine_rank": no_fine_rank_pipeline_fn,
    "no_context_enrich": no_context_enrich_pipeline_fn,
}
