"""
RAG 管线 StateGraph —— 将检索决策 / Query 改写 / 搜索 / 上下文构建编排为 LangGraph 图。

三个节点:
  decide_kb        → should_search_kb() 判断 need_kb / skip_rewrite
  fast_path        → skip_rewrite 时：直接搜索 + 构建上下文
  rewrite_and_search → 需要 LLM 改写时：并行执行 Query 改写 + 上下文构建

chat.py 中的 if/else 分支被替换为单次 graph.ainvoke() 调用，
功能与原有行为完全等价。
"""

import asyncio
import logging
from typing import Any, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, END

from app.services.chat import chat_pipeline, query_rewriter
from app.services.memory.context_builder import context_builder

logger = logging.getLogger(__name__)


# ── 状态定义 ──────────────────────────────────────────────────

class RAGState(TypedDict, total=False):
    """RAG 管线状态。

    节点之间通过该 dict 共享数据，初始值由 chat.py 注入。
    """
    message: str
    session_id: str
    user_id: int
    db: AsyncSession
    org_id: str | None
    need_kb: bool
    skip_rewrite: bool
    context_messages: list[dict]
    search_results: list[dict]


# ── 节点函数 ──────────────────────────────────────────────────

async def _decide_kb_node(state: RAGState) -> dict:
    """节点0: 判断是否需要知识库搜索、是否跳过 Query 改写。"""
    msg = state["message"]
    need_kb, skip_rewrite = chat_pipeline.should_search_kb(msg)
    logger.info(
        "[RAG Graph] decide_kb: need_kb=%s, skip_rewrite=%s",
        need_kb, skip_rewrite
    )
    return {"need_kb": need_kb, "skip_rewrite": skip_rewrite}


async def _fast_path_node(state: RAGState) -> dict:
    """节点1a: skip_rewrite 路径 —— 无需 LLM 改写。"""
    msg = state["message"]
    need_kb = state["need_kb"]
    db = state["db"]
    sid = state["session_id"]
    uid = state["user_id"]
    org_id = state.get("org_id")

    rewrite_result = chat_pipeline.build_rewrite_result(msg, state["skip_rewrite"])
    chat_pipeline.log_rewrite_result(rewrite_result)

    search_results = []
    if need_kb:
        search_results = await chat_pipeline.search_knowledge_base(msg, org_id=org_id)

    ctx = await context_builder.build(db, sid, uid, msg)
    return {
        "search_results": search_results,
        "context_messages": ctx.messages,
    }


async def _rewrite_and_search_node(state: RAGState) -> dict:
    """节点1b: 需要 LLM Query 改写 —— 并行执行改写 + 上下文构建。"""
    msg = state["message"]
    need_kb = state["need_kb"]
    db = state["db"]
    sid = state["session_id"]
    uid = state["user_id"]
    org_id = state.get("org_id")

    # 与改写请求并行启动上下文构建（匹配原有 asyncio.create_task 行为）
    ctx_task = asyncio.create_task(
        context_builder.build(db, sid, uid, msg)
    )

    rewrite_result = await query_rewriter.rewrite(msg)
    chat_pipeline.log_rewrite_result(rewrite_result)

    search_results = []
    if need_kb:
        search_query = rewrite_result["rewritten_query"]
        search_results = await chat_pipeline.search_knowledge_base(search_query, org_id=org_id)
        search_results = await chat_pipeline.merge_expanded_results(
            search_results, rewrite_result, org_id=org_id
        )

    ctx = await ctx_task
    return {
        "search_results": search_results,
        "context_messages": ctx.messages,
    }


# ── 条件路由 ──────────────────────────────────────────────────

def _route_after_decide(state: RAGState) -> str:
    """decide_kb 之后的分支: skip_rewrite → fast_path 否则 rewrite_and_search。"""
    if state.get("skip_rewrite", False):
        return "fast_path"
    return "rewrite_and_search"


# ── 图构建 ────────────────────────────────────────────────────

_builder = StateGraph(RAGState)
_builder.add_node("decide_kb", _decide_kb_node)
_builder.add_node("fast_path", _fast_path_node)
_builder.add_node("rewrite_and_search", _rewrite_and_search_node)

_builder.set_entry_point("decide_kb")
_builder.add_conditional_edges(
    "decide_kb",
    _route_after_decide,
    {
        "fast_path": "fast_path",
        "rewrite_and_search": "rewrite_and_search",
    },
)
_builder.add_edge("fast_path", END)
_builder.add_edge("rewrite_and_search", END)

rag_graph = _builder.compile()
