import asyncio
import json
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, async_session
from app.core.config import settings
from app.core.dependencies import CurrentUser
from app.schemas.chat import ChatRequest
from app.schemas.conversation import SessionOut, SessionDetailOut, SessionCreate, SessionUpdate, SessionPinUpdate
from app.services.chat_service import chat_service
from app.services.conversation_service import conversation_service
from app.services.memory.context_builder import context_builder
from app.services.reranker_service import reranker_service
from app.services.query_rewriter import query_rewriter
from app.services.bm25_service import bm25_service
from app.services.embedding import embedding_service, BGE_QUERY_INSTRUCTION
from app.services.milvus_service import milvus_service
from app.services.tools import tool_executor
from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])


async def _kb_search_fn(query: str) -> list:
    results = await asyncio.to_thread(reranker_service.search_and_rerank, query)
    return results


tool_executor.set_search_fn(_kb_search_fn)


def _log_rewrite_result(rewrite_result: dict):
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


async def _merge_expanded_results(main_results: list, rewrite_result: dict) -> list:
    expanded_queries = rewrite_result.get("expanded_queries", [])
    if not expanded_queries:
        return main_results

    seen_keys = set()
    for r in main_results:
        key = f"{r.get('document_id', '')}_{r.get('chunk_index', 0)}"
        seen_keys.add(key)

    threshold = settings.SIMILARITY_THRESHOLD

    async def _search_one_expanded(eq: str):
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
        except Exception as e:
            logger.warning(f"[Query改写] 扩展查询 '{eq}' 检索失败: {e}")
            return []

    all_expanded_results = await asyncio.gather(*[_search_one_expanded(eq) for eq in expanded_queries])

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


@router.post("/ask")
async def ask(
    req: ChatRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        session_id = req.session_id
        if session_id:
            session = await conversation_service.get_session(db, session_id, current_user.id)
            if not session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        else:
            session = await conversation_service.create_session(db, current_user.id)
            session_id = session.id

        await conversation_service.save_message(db, session_id, "user", req.message)

        if req.quick_mode:
            logger.info(f"[快速模式] 跳过RAG管线，直接回复: {req.message}")

            history_messages = []
            try:
                ctx = await context_builder.build(db, session_id, current_user.id, req.message)
                history_messages = ctx.messages
            except Exception:
                pass

            result = await chat_service.quick_ask(req.message, history_messages)
        else:
            need_kb = query_rewriter.needs_knowledge_base(req.message)
            skip_rewrite = query_rewriter.should_skip_rewrite(req.message)

            if skip_rewrite:
                logger.info(f"[Query改写] 检测到简单/工具类查询，跳过 LLM 改写: {req.message}")
                rewrite_result = {
                    "original_query": req.message,
                    "rewritten_query": req.message,
                    "expanded_queries": []
                }
                _log_rewrite_result(rewrite_result)

                if need_kb:
                    search_results = await asyncio.to_thread(
                        reranker_service.search_and_rerank, req.message
                    )
                    if search_results:
                        logger.info(f"[对话] 检索到 {len(search_results)} 条相关文档")
                else:
                    search_results = []

                ctx = await context_builder.build(db, session_id, current_user.id, req.message)
            else:
                ctx_task = asyncio.create_task(
                    context_builder.build(db, session_id, current_user.id, req.message)
                )

                rewrite_result = await query_rewriter.rewrite(req.message)
                _log_rewrite_result(rewrite_result)

                if need_kb:
                    search_query = rewrite_result["rewritten_query"]
                    search_results = await asyncio.to_thread(
                        reranker_service.search_and_rerank, search_query
                    )
                    search_results = await _merge_expanded_results(search_results, rewrite_result)
                    if search_results:
                        logger.info(f"[对话] 检索到 {len(search_results)} 条相关文档")
                else:
                    search_results = []

                ctx = await ctx_task

            result = await chat_service.ask(req.message, ctx.messages, search_results)

        await conversation_service.save_message(db, session_id, "assistant", result["answer"])

        await conversation_service.extract_and_save_long_term(db, current_user.id, session_id)

        return {
            "code": 0,
            "message": "success",
            "data": {
                "answer": result["answer"],
                "model": result["model"],
                "session_id": session_id,
                "tool_calls": result.get("tool_calls", [])
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/stream")
async def stream_chat(
    req: ChatRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    logger.info(f"[对话] 收到请求，quick_mode={req.quick_mode}, message={req.message[:50]}..., images={len(req.images) if req.images else 0}")
    session_id = req.session_id
    if session_id:
        session = await conversation_service.get_session(db, session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    else:
        session = await conversation_service.create_session(db, current_user.id)
        session_id = session.id

    await conversation_service.save_message(db, session_id, "user", req.message)

    async def event_generator():
        collected_content = []
        voice_param = req.voice or "longanhuan"
        try:
            if req.images and len(req.images) > 0:
                logger.info(f"[视觉模式] 使用视觉模型处理图片，数量: {len(req.images)}")
                yield f"data: {json.dumps({'s': 'analyzing'})}\n\n"
                yield f"data: {json.dumps({'session_id': session_id})}\n\n"

                history_messages = []
                try:
                    ctx = await context_builder.build(db, session_id, current_user.id, req.message)
                    history_messages = ctx.messages
                except Exception:
                    pass

                yield f"data: {json.dumps({'s': 'generating'})}\n\n"
                async for event in chat_service.stream_vision_ask(req.message, req.images, history_messages):
                    event_type = event.get("type", "content")
                    if event_type == "content":
                        collected_content.append(event["content"])
                        yield f"data: {json.dumps({'c': event['content']})}\n\n"
                    elif event_type == "tool_call":
                        yield f"data: {json.dumps({'tc': {'tool_name': event['tool_name'], 'tool_args': event['tool_args'], 'tool_call_id': event['tool_call_id']}})}\n\n"
                    elif event_type == "tool_result":
                        yield f"data: {json.dumps({'tr': {'tool_name': event['tool_name'], 'result': event['result'], 'tool_call_id': event['tool_call_id']}})}\n\n"
                    elif event_type == "error":
                        yield f"data: {json.dumps({'error': event['content']})}\n\n"
            elif req.quick_mode:
                logger.info(f"[快速模式] 跳过RAG管线，直接回复: {req.message}")
                yield f"data: {json.dumps({'s': 'generating'})}\n\n"
                yield f"data: {json.dumps({'session_id': session_id})}\n\n"

                history_messages = []
                try:
                    ctx = await context_builder.build(db, session_id, current_user.id, req.message)
                    history_messages = ctx.messages
                except Exception:
                    pass

                async for event in chat_service.stream_quick_ask(req.message, history_messages):
                    event_type = event.get("type", "content")
                    if event_type == "content":
                        collected_content.append(event["content"])
                        yield f"data: {json.dumps({'c': event['content']})}\n\n"
                    elif event_type == "tool_call":
                        yield f"data: {json.dumps({'tc': {'tool_name': event['tool_name'], 'tool_args': event['tool_args'], 'tool_call_id': event['tool_call_id']}})}\n\n"
                    elif event_type == "tool_result":
                        yield f"data: {json.dumps({'tr': {'tool_name': event['tool_name'], 'result': event['result'], 'tool_call_id': event['tool_call_id']}})}\n\n"
                    elif event_type == "error":
                        yield f"data: {json.dumps({'error': event['content']})}\n\n"
            else:
                need_kb = query_rewriter.needs_knowledge_base(req.message)
                skip_rewrite = query_rewriter.should_skip_rewrite(req.message)

                ctx_task = asyncio.create_task(
                    context_builder.build(db, session_id, current_user.id, req.message)
                )

                if skip_rewrite:
                    logger.info(f"[Query改写] 检测到简单/工具类查询，跳过 LLM 改写: {req.message}")
                    rewrite_result = {
                        "original_query": req.message,
                        "rewritten_query": req.message,
                        "expanded_queries": []
                    }
                else:
                    yield f"data: {json.dumps({'s': 'analyzing'})}\n\n"
                    rewrite_result = await query_rewriter.rewrite(req.message)
                _log_rewrite_result(rewrite_result)

                if need_kb:
                    yield f"data: {json.dumps({'s': 'retrieving'})}\n\n"
                    search_query = rewrite_result["rewritten_query"]
                    search_results = await asyncio.to_thread(
                        reranker_service.search_and_rerank, search_query
                    )
                    search_results = await _merge_expanded_results(search_results, rewrite_result)
                    if search_results:
                        logger.info(f"[对话] 检索到 {len(search_results)} 条相关文档")
                else:
                    logger.info(f"[对话] 工具类/闲聊查询，跳过知识库检索: {req.message}")
                    search_results = []

                yield f"data: {json.dumps({'s': 'generating'})}\n\n"

                ctx = await ctx_task

                yield f"data: {json.dumps({'session_id': session_id})}\n\n"
                async for event in chat_service.stream_ask(req.message, ctx.messages, search_results):
                    event_type = event.get("type", "content")
                    if event_type == "content":
                        collected_content.append(event["content"])
                        yield f"data: {json.dumps({'c': event['content']})}\n\n"
                    elif event_type == "tool_call":
                        yield f"data: {json.dumps({'tc': {'tool_name': event['tool_name'], 'tool_args': event['tool_args'], 'tool_call_id': event['tool_call_id']}})}\n\n"
                    elif event_type == "tool_result":
                        yield f"data: {json.dumps({'tr': {'tool_name': event['tool_name'], 'result': event['result'], 'tool_call_id': event['tool_call_id']}})}\n\n"
                    elif event_type == "error":
                        yield f"data: {json.dumps({'error': event['content']})}\n\n"

            full_answer = "".join(collected_content)
            async with async_session() as save_db:
                await conversation_service.save_message(save_db, session_id, "assistant", full_answer)
                await conversation_service.extract_and_save_long_term(save_db, current_user.id, session_id)

            if full_answer.strip():
                logger.info(f"[TTS] 开始合成完整回答, 文本长度: {len(full_answer)}")
                try:
                    chunk_count = 0
                    async for chunk in voice_service.text_to_speech_stream(full_answer, voice_param):
                        chunk_count += 1
                        yield f"data: {json.dumps({'a': chunk})}\n\n"
                    logger.info(f"[TTS] 合成完成, 共 {chunk_count} 个音频块")
                except Exception as e:
                    logger.error(f"[TTS] 合成失败: {e}")

            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/sessions", response_model=dict)
async def list_sessions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    sessions = await conversation_service.list_sessions(db, current_user.id, limit, offset)
    return {
        "code": 0,
        "message": "success",
        "data": [SessionOut.model_validate(s).model_dump(mode="json") for s in sessions]
    }


@router.post("/sessions", response_model=dict)
async def create_session(
    req: SessionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    session = await conversation_service.create_session(db, current_user.id, req.title)
    return {
        "code": 0,
        "message": "success",
        "data": SessionOut.model_validate(session).model_dump(mode="json")
    }


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session_detail(
    session_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    session = await conversation_service.get_session_with_messages(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return {
        "code": 0,
        "message": "success",
        "data": SessionDetailOut.model_validate(session).model_dump(mode="json")
    }


@router.patch("/sessions/{session_id}", response_model=dict)
async def update_session(
    session_id: str,
    req: SessionUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if req.title is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要提供title字段")
    session = await conversation_service.update_session_title(db, session_id, current_user.id, req.title)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return {
        "code": 0,
        "message": "success",
        "data": SessionOut.model_validate(session).model_dump(mode="json")
    }


@router.patch("/sessions/{session_id}/pin", response_model=dict)
async def toggle_pin_session(
    session_id: str,
    req: SessionPinUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    session = await conversation_service.toggle_pin(db, session_id, current_user.id, req.is_pinned)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return {
        "code": 0,
        "message": "success",
        "data": SessionOut.model_validate(session).model_dump(mode="json")
    }


@router.delete("/sessions/{session_id}", response_model=dict)
async def delete_session(
    session_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    deleted = await conversation_service.delete_session(db, session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return {"code": 0, "message": "success", "data": None}


@router.get("/preferences", response_model=dict)
async def get_preferences(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    from app.services.memory.long_term import long_term_memory
    prefs = await long_term_memory.load(db, current_user.id)
    return {"code": 0, "message": "success", "data": prefs}
