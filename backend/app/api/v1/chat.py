import asyncio
import json
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, async_session
from app.core.dependencies import CurrentUser, CurrentOrganization
from app.schemas.chat import ChatRequest
from app.schemas.conversation import SessionOut, SessionDetailOut, SessionCreate, SessionUpdate, SessionPinUpdate
from app.services.chat import chat_service, chat_pipeline, conversation_service, voice_service, query_rewriter
from app.services.chat.conversation import get_user_stats
from app.services.chat.pipeline import org_id_context
from app.services.chat.engine.rag_graph import rag_graph, RAGState
from app.services.memory.context_builder import context_builder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])

chat_pipeline.bind_kb_search()


# ── 辅助函数 ──────────────────────────────────────────────────

def _extract_source_documents(search_results: list) -> list:
    seen = set()
    sources = []
    for r in search_results:
        doc_id = r.get("document_id", "")
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            sources.append({
                "title": r.get("title", ""),
                "document_id": doc_id,
            })
    return sources


def _event_to_sse(event: dict) -> dict:
    event_type = event.get("type", "content")
    if event_type == "content":
        return {"c": event["content"]}
    elif event_type == "tool_call":
        return {"tc": {"tool_name": event["tool_name"], "tool_args": event["tool_args"], "tool_call_id": event["tool_call_id"]}}
    elif event_type == "tool_result":
        return {"tr": {"tool_name": event["tool_name"], "result": event["result"], "tool_call_id": event["tool_call_id"]}}
    elif event_type == "error":
        return {"error": event["content"]}
    return {}


@router.post("/ask")
async def ask(
    req: ChatRequest,
    current_user: CurrentUser,
    org_context: CurrentOrganization,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        org, member = org_context
        org_id = org.id if org else None
        org_id_context.set(org_id)

        session_id = req.session_id
        kb_doc_ids = None
        kb_name = None
        if req.knowledge_base_id:
            from app.services.knowledge_base_service import knowledge_base_service
            kb = await knowledge_base_service.get(db, req.knowledge_base_id)
            if not kb:
                raise HTTPException(status_code=404, detail="知识库不存在")
            kb_name = kb.name
            kb_doc_ids_list = await knowledge_base_service.get_document_ids(db, req.knowledge_base_id)
            kb_doc_ids = kb_doc_ids_list

            if kb.owner_id != str(current_user.id):
                member_info = await knowledge_base_service.get_user_member_info(
                    db, req.knowledge_base_id, str(current_user.id)
                )
                if not member_info["is_joined"]:
                    msg_count = await knowledge_base_service.count_user_kb_messages(
                        db, req.knowledge_base_id, str(current_user.id)
                    )
                    if msg_count >= 3:
                        raise HTTPException(
                            status_code=403,
                            detail="您已用完免费对话次数，请加入知识库后继续对话"
                        )

        # 使用知识库作者的组织ID进行检索，确保能检索到作者上传的文档
        from app.models.organization import OrganizationMember
        from sqlalchemy import select as sa_select
        owner_org_result = await db.execute(
            sa_select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id == kb.owner_id,
                OrganizationMember.is_active == True
            ).limit(1)
        )
        owner_org_id = owner_org_result.scalar_one_or_none()
        if owner_org_id:
            org_id = str(owner_org_id)
            org_id_context.set(str(owner_org_id))

        if session_id:
            session = await conversation_service.get_session(db, session_id, current_user.id)
            if not session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        else:
            session = await conversation_service.create_session(
                db, current_user.id,
                knowledge_base_id=req.knowledge_base_id,
                knowledge_base_name=kb_name,
            )
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
            result = await chat_service.quick_ask(req.message, history_messages, req.personalization)
        else:
            # ── RAG 管线由 StateGraph 编排 ──
            initial: RAGState = {
                "message": req.message,
                "session_id": session_id,
                "user_id": current_user.id,
                "db": db,
                "org_id": org_id,
                "document_ids": kb_doc_ids,
            }
            state = await rag_graph.ainvoke(initial)
            result = await chat_service.ask(
                req.message,
                state["context_messages"],
                state["search_results"],
                req.personalization,
            )

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
    except Exception as e:
        logger.exception(f"[ask] 未预期错误: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/stream")
async def stream_chat(
    req: ChatRequest,
    current_user: CurrentUser,
    org_context: CurrentOrganization,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    logger.info(f"[对话] 收到请求，quick_mode={req.quick_mode}, message={req.message[:50]}..., images={len(req.images) if req.images else 0}")
    org, member = org_context
    org_id = org.id if org else None
    org_id_context.set(org_id)

    session_id = req.session_id
    kb_doc_ids = None
    kb_name = None
    kb_org_id = None
    if req.knowledge_base_id:
        from app.services.knowledge_base_service import knowledge_base_service
        kb = await knowledge_base_service.get(db, req.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        kb_name = kb.name
        kb_doc_ids_list = await knowledge_base_service.get_document_ids(db, req.knowledge_base_id)
        kb_doc_ids = kb_doc_ids_list

        if kb.owner_id != str(current_user.id):
            member_info = await knowledge_base_service.get_user_member_info(
                db, req.knowledge_base_id, str(current_user.id)
            )
            if not member_info["is_joined"]:
                msg_count = await knowledge_base_service.count_user_kb_messages(
                    db, req.knowledge_base_id, str(current_user.id)
                )
                if msg_count >= 3:
                    raise HTTPException(
                        status_code=403,
                        detail="您已用完免费对话次数，请加入知识库后继续对话"
                    )

        from app.models.organization import OrganizationMember
        from sqlalchemy import select as sa_select
        owner_org_result = await db.execute(
            sa_select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id == kb.owner_id,
                OrganizationMember.is_active == True
            ).limit(1)
        )
        owner_org_id = owner_org_result.scalar_one_or_none()
        if owner_org_id:
            kb_org_id = owner_org_id
            org_id = str(owner_org_id)
            org_id_context.set(str(owner_org_id))

    if session_id:
        session = await conversation_service.get_session(db, session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    else:
        session = await conversation_service.create_session(
            db, current_user.id,
            knowledge_base_id=req.knowledge_base_id,
            knowledge_base_name=kb_name,
        )
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
                async for event in chat_service.stream_vision_ask(req.message, req.images, history_messages, req.personalization):
                    if event["type"] == "content":
                        collected_content.append(event["content"])
                    yield f"data: {json.dumps(_event_to_sse(event))}\n\n"
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

                async for event in chat_service.stream_quick_ask(req.message, history_messages, req.personalization):
                    if event["type"] == "content":
                        collected_content.append(event["content"])
                    yield f"data: {json.dumps(_event_to_sse(event))}\n\n"
            else:
                # ── RAG 管线由 StateGraph 编排 ──
                need_kb, skip_rewrite = chat_pipeline.should_search_kb(req.message)

                initial: RAGState = {
                    "message": req.message,
                    "session_id": session_id,
                    "user_id": current_user.id,
                    "db": db,
                    "org_id": org_id,
                    "document_ids": kb_doc_ids,
                }

                # SSE: analyzing（仅 LLM 改写时发送）
                if not skip_rewrite:
                    yield f"data: {json.dumps({'s': 'analyzing'})}\n\n"

                state = await rag_graph.ainvoke(initial)

                # SSE: 检索状态
                search_results = state["search_results"]
                if need_kb:
                    yield f"data: {json.dumps({'s': 'retrieving'})}\n\n"
                    logger.info(f"[对话] 知识库查询模式, need_kb=True, 检索到 {len(search_results)} 条结果")

                if search_results:
                    source_docs = _extract_source_documents(search_results)
                    logger.info(f"[对话] 提取来源文档: {len(source_docs)} 个, titles: {[d['title'] for d in source_docs]}")
                    if source_docs:
                        yield f"data: {json.dumps({'src': source_docs})}\n\n"
                else:
                    logger.info("[对话] 无搜索结果，不发送来源事件")

                # SSE: 生成中
                yield f"data: {json.dumps({'s': 'generating'})}\n\n"
                yield f"data: {json.dumps({'session_id': session_id})}\n\n"

                async for event in chat_service.stream_ask(req.message, state["context_messages"], search_results, req.personalization):
                    if event["type"] == "content":
                        collected_content.append(event["content"])
                    yield f"data: {json.dumps(_event_to_sse(event))}\n\n"

            full_answer = "".join(collected_content)
            async with async_session() as save_db:
                await conversation_service.save_message(save_db, session_id, "assistant", full_answer)
                await conversation_service.extract_and_save_long_term(save_db, current_user.id, session_id)

            yield "data: [DONE]\n\n"

            if full_answer.strip():
                logger.info(f"[TTS] 开始合成完整回答, 文本长度: {len(full_answer)}")
                try:
                    chunk_count = 0
                    async for chunk in voice_service.text_to_speech_stream(full_answer, voice_param):
                        chunk_count += 1
                        try:
                            yield f"data: {json.dumps({'a': chunk})}\n\n"
                        except BaseException:
                            logger.info(f"[TTS] 客户端已断开, 停止发送音频 (已发送 {chunk_count} 块)")
                            return
                    logger.info(f"[TTS] 合成完成, 共 {chunk_count} 个音频块")
                except Exception as e:
                    logger.error(f"[TTS] 合成失败: {e}")
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


@router.get("/stats", response_model=dict)
async def get_chat_stats(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stats = await get_user_stats(db, str(current_user.id))
    return {"code": 0, "message": "success", "data": stats}


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