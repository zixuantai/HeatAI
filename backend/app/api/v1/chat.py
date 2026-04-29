import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, async_session
from app.core.dependencies import CurrentUser
from app.schemas.chat import ChatRequest
from app.schemas.conversation import SessionOut, SessionDetailOut, SessionCreate, SessionUpdate
from app.services.chat_service import chat_service
from app.services.conversation_service import conversation_service
from app.services.memory.context_builder import context_builder

router = APIRouter(prefix="/chat", tags=["对话"])


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

        ctx = await context_builder.build(db, session_id, current_user.id, req.message)

        result = await chat_service.ask(req.message, ctx.messages)

        await conversation_service.save_message(db, session_id, "assistant", result["answer"])

        await conversation_service.extract_and_save_long_term(db, current_user.id, session_id)

        return {
            "code": 0,
            "message": "success",
            "data": {"answer": result["answer"], "model": result["model"], "session_id": session_id}
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
    session_id = req.session_id
    if session_id:
        session = await conversation_service.get_session(db, session_id, current_user.id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    else:
        session = await conversation_service.create_session(db, current_user.id)
        session_id = session.id

    await conversation_service.save_message(db, session_id, "user", req.message)

    ctx = await context_builder.build(db, session_id, current_user.id, req.message)

    async def event_generator():
        collected_content = []
        try:
            yield f"data: {json.dumps({'session_id': session_id})}\n\n"
            async for content in chat_service.stream_ask(req.message, ctx.messages):
                collected_content.append(content)
                yield f"data: {json.dumps({'c': content})}\n\n"

            full_answer = "".join(collected_content)
            async with async_session() as save_db:
                await conversation_service.save_message(save_db, session_id, "assistant", full_answer)
                await conversation_service.extract_and_save_long_term(save_db, current_user.id, session_id)

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
