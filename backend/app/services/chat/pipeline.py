import asyncio
import contextvars
import logging
from app.services.retrieval.reranker_service import reranker_service
from app.services.chat.engine.query_rewriter import query_rewriter
from app.services.retrieval.bm25_service import bm25_service
from app.services.retrieval.embedding import embedding_service, BGE_QUERY_INSTRUCTION
from app.services.retrieval.milvus_service import milvus_service
from app.services.chat.engine.tools import tool_executor
from app.core.config import settings

logger = logging.getLogger(__name__)

org_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("org_id", default=None)


class ChatPipeline:

    def __init__(self):
        self._kb_search_bound = False

    def bind_kb_search(self):
        if not self._kb_search_bound:
            async def _kb_search_fn(query: str) -> list:
                org_id = org_id_context.get()
                results = await asyncio.to_thread(reranker_service.search_and_rerank, query, org_id=org_id)
                return results

            tool_executor.set_search_fn(_kb_search_fn)
            from app.services.chat.engine.tools import set_kb_search_fn
            set_kb_search_fn(_kb_search_fn)
            self._kb_search_bound = True

    @staticmethod
    def log_rewrite_result(rewrite_result: dict):
        logger.info("=" * 60)
        logger.info(f"[Query改写] 原始查询: {rewrite_result['original_query']}")
        logger.info(f"[Query改写] 改写查询: {rewrite_result['rewritten_query']}")
        expanded = rewrite_result.get("expanded_queries", [])
        if expanded:
            for i, eq in enumerate(expanded):
                logger.info(f"[Query改写] 扩展查询{i + 1}: {eq}")
        else:
            logger.info("[Query改写] 无扩展查询")
        logger.info("=" * 60)

    @staticmethod
    async def merge_expanded_results(
        main_results: list,
        rewrite_result: dict,
        org_id: str | None = None,
        document_ids: list[str] | None = None,
        knowledge_base_id: str | None = None,
    ) -> list:
        expanded_queries = rewrite_result.get("expanded_queries", [])
        if not expanded_queries:
            return main_results

        threshold = settings.SIMILARITY_THRESHOLD

        if main_results:
            min_score = settings.EXPANDED_MIN_MAIN_SCORE
            min_count = settings.EXPANDED_SKIP_COUNT
            high_quality = sum(1 for r in main_results if r.get("score", 0) >= min_score)
            if len(main_results) >= min_count and high_quality >= min(2, len(main_results)):
                logger.info(
                    f"[Query改写] 主检索结果充足 (共{len(main_results)}条, 高分{high_quality}条), 跳过扩展查询"
                )
                return main_results

        seen_keys = set()
        for r in main_results:
            key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
            seen_keys.add(key)

        expanded_texts = [BGE_QUERY_INSTRUCTION + eq for eq in expanded_queries]
        expanded_embs = await asyncio.to_thread(embedding_service.encode, expanded_texts)

        async def _search_one_expanded(eq: str, query_emb: list):
            try:
                bm25_task = asyncio.to_thread(bm25_service.search, eq, 3, org_id, document_ids, knowledge_base_id)
                milvus_task = asyncio.to_thread(milvus_service.search, query_emb, 3, org_id, document_ids, knowledge_base_id)
                bm25_res_raw, vector_res_raw = await asyncio.gather(bm25_task, milvus_task)

                bm25_res = reranker_service.filter_by_threshold(bm25_res_raw, threshold)
                vector_res = reranker_service.filter_by_threshold(vector_res_raw, threshold)
                for r in vector_res:
                    r["retriever"] = "vector_expanded"
                merged = list(bm25_res)
                bm25_keys = {f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}" for r in bm25_res}
                for r in vector_res:
                    key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
                    if key not in bm25_keys:
                        merged.append(r)
                return merged
            except Exception as e:
                logger.warning(f"[Query改写] 扩展查询 '{eq}' 检索失败: {e}")
                return []

        all_expanded_results = await asyncio.gather(*[
            _search_one_expanded(eq, emb) for eq, emb in zip(expanded_queries, expanded_embs)
        ])

        merged = list(main_results)
        for exp_results in all_expanded_results:
            for r in exp_results:
                key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    if "retriever" not in r:
                        r["retriever"] = "bm25_expanded"
                    merged.append(r)

        if len(merged) > len(main_results):
            logger.info(f"[Query改写] 扩展查询新增 {len(merged) - len(main_results)} 条召回结果，合并后共 {len(merged)} 条")

        return merged

    @staticmethod
    def build_rewrite_result(message: str, skip_rewrite: bool):
        if skip_rewrite:
            logger.info(f"[Query改写] 检测到简单/工具类查询，跳过 LLM 改写: {message}")
            return {
                "original_query": message,
                "rewritten_query": message,
                "expanded_queries": []
            }
        return None

    @staticmethod
    async def search_knowledge_base(message: str, org_id: str | None = None, document_ids: list[str] | None = None, knowledge_base_id: str | None = None) -> list:
        results = await asyncio.to_thread(reranker_service.search_and_rerank, message, org_id=org_id, document_ids=document_ids, knowledge_base_id=knowledge_base_id)
        if results:
            logger.info(f"[对话] 检索到 {len(results)} 条相关文档")
        return results

    @staticmethod
    def should_search_kb(message: str) -> bool:
        need_kb = query_rewriter.needs_knowledge_base(message)
        skip_rewrite = query_rewriter.should_skip_rewrite(message)
        return need_kb, skip_rewrite


chat_pipeline = ChatPipeline()
