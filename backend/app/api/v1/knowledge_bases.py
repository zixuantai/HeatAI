import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.core.database import get_db
from app.core.dependencies import CurrentUser, CurrentOrganization
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    QuickQuestionsPreviewIn,
    KnowledgeBaseListResponse,
    QuickQuestionsUpdate,
    KBChatRequest,
)
from app.services.knowledge_base_service import knowledge_base_service
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["知识库广场"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.create(
        db=db,
        owner_id=str(current_user.id),
        owner_name=current_user.username,
        name=body.name,
        description=body.description,
        avatar=body.avatar,
        cover_color=body.cover_color,
        quick_questions=body.quick_questions,
    )
    return {
        "code": 0,
        "message": "知识库创建成功",
        "data": KnowledgeBaseOut.model_validate(kb).model_dump(mode="json"),
    }


@router.get("", response_model=dict)
async def list_knowledge_bases(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=200),
    sort_by: str = Query(default="latest", pattern="^(latest|popular|recommended|mine|joined)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    bases, total = await knowledge_base_service.list_bases(
        db=db,
        user_id=str(current_user.id),
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    items = []
    for kb in bases:
        interactions = await knowledge_base_service.get_user_interactions(
            db, kb.id, str(current_user.id)
        )
        kb_out = KnowledgeBaseOut.model_validate(kb)
        kb_out.is_liked = interactions["is_liked"]
        kb_out.is_favorited = interactions["is_favorited"]
        items.append(kb_out.model_dump(mode="json"))
    return {
        "code": 0,
        "message": "success",
        "data": {"total": total, "items": items},
    }


@router.get("/{kb_id}", response_model=dict)
async def get_knowledge_base(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    kb_data = KnowledgeBaseOut.model_validate(kb).model_dump()
    kb_data["view_count"] += 1
    kb_data["is_liked"] = False
    kb_data["is_favorited"] = False

    await knowledge_base_service.increment_view(db, kb_id)

    interactions = await knowledge_base_service.get_user_interactions(
        db, kb_id, str(current_user.id)
    )
    kb_data["is_liked"] = interactions["is_liked"]
    kb_data["is_favorited"] = interactions["is_favorited"]

    member_info = await knowledge_base_service.get_user_member_info(
        db, kb_id, str(current_user.id)
    )
    kb_data["is_joined"] = member_info["is_joined"]
    member_ids = await knowledge_base_service.list_member_ids(db, kb_id)
    kb_data["member_count"] = len(member_ids)

    # 获取创建者头像
    from app.models.user import User
    owner_result = await db.execute(
        select(User.avatar).where(User.id == kb.owner_id)
    )
    owner_avatar = owner_result.scalar_one_or_none()
    kb_data["owner_avatar"] = owner_avatar or kb.avatar

    return {
        "code": 0,
        "message": "success",
        "data": kb_data,
    }


@router.put("/{kb_id}", response_model=dict)
async def update_knowledge_base(
    kb_id: str,
    body: KnowledgeBaseUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.update(
        db=db,
        kb_id=kb_id,
        owner_id=str(current_user.id),
        name=body.name,
        description=body.description,
        avatar=body.avatar,
        cover_color=body.cover_color,
        quick_questions=body.quick_questions,
        is_recommended=body.is_recommended,
    )
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在或无权限修改")
    return {
        "code": 0,
        "message": "知识库更新成功",
        "data": KnowledgeBaseOut.model_validate(kb).model_dump(mode="json"),
    }


@router.delete("/{kb_id}", response_model=dict)
async def delete_knowledge_base(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    success = await knowledge_base_service.delete(db, kb_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="知识库不存在或无权限删除")
    return {"code": 0, "message": "知识库已删除", "data": None}


@router.post("/{kb_id}/like", response_model=dict)
async def toggle_like(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    is_liked = await knowledge_base_service.toggle_like(db, kb_id, str(current_user.id))
    return {
        "code": 0,
        "message": "点赞成功" if is_liked else "取消点赞",
        "data": {"is_liked": is_liked},
    }


@router.post("/{kb_id}/favorite", response_model=dict)
async def toggle_favorite(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    is_favorited = await knowledge_base_service.toggle_favorite(db, kb_id, str(current_user.id))
    return {
        "code": 0,
        "message": "收藏成功" if is_favorited else "取消收藏",
        "data": {"is_favorited": is_favorited},
    }


@router.put("/{kb_id}/quick-questions", response_model=dict)
async def update_quick_questions(
    kb_id: str,
    body: QuickQuestionsUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.update(
        db=db,
        kb_id=kb_id,
        owner_id=str(current_user.id),
        quick_questions=body.quick_questions,
    )
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在或无权限修改")
    return {
        "code": 0,
        "message": "快捷问题更新成功",
        "data": {"quick_questions": kb.quick_questions},
    }


@router.post("/{kb_id}/join", response_model=dict)
async def toggle_join_knowledge_base(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.status != "active":
        raise HTTPException(status_code=400, detail="知识库已下线")

    joined, member_count = await knowledge_base_service.toggle_join(
        db, kb_id, str(current_user.id)
    )
    return {
        "code": 0,
        "message": "已加入知识库" if joined else "已退出知识库",
        "data": {"is_joined": joined, "member_count": member_count},
    }


@router.get("/{kb_id}/documents", response_model=dict)
async def list_knowledge_base_documents(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    documents, total = await knowledge_base_service.list_documents(db, kb_id, limit, offset)
    from app.schemas.document import DocumentInfo
    items = [DocumentInfo.model_validate(doc).model_dump(mode="json") for doc in documents]
    return {
        "code": 0,
        "message": "success",
        "data": {"total": total, "items": items},
    }


@router.post("/{kb_id}/documents/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document_to_kb(
    kb_id: str,
    current_user: CurrentUser,
    org_context: CurrentOrganization,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    from app.services.document_service import document_service
    from app.services.processing.parser import DocumentParser

    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    supported = tuple(DocumentParser.SUPPORTED_TYPES)
    if ext not in supported:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: .{ext}")

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 50MB")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="文件不能为空")

    org, member = org_context
    upload_org_id = str(org.id) if org else None

    try:
        document = await document_service.upload_and_process(
            db=db,
            user_id=str(current_user.id),
            file_bytes=file_bytes,
            original_filename=file.filename,
            org_id=upload_org_id,
            knowledge_base_id=kb_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.exception(f"文档上传运行时异常: {file.filename} - {e}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {e}")
    except Exception as e:
        logger.exception(f"文档上传处理异常: {file.filename} - {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {e}")

    await knowledge_base_service.add_document(db, kb_id, document.id)

    return {
        "code": 0,
        "message": "文档上传成功",
        "data": {
            "document_id": document.id,
            "filename": document.original_filename,
            "status": document.status,
        },
    }


@router.post("/{kb_id}/documents/{document_id}", response_model=dict)
async def add_document_to_knowledge_base(
    kb_id: str,
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    link = await knowledge_base_service.add_document(db, kb_id, document_id)
    return {
        "code": 0,
        "message": "文档添加成功",
        "data": {"id": link.id},
    }


@router.delete("/{kb_id}/documents/{document_id}", response_model=dict)
async def remove_document_from_knowledge_base(
    kb_id: str,
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    success = await knowledge_base_service.remove_document(db, kb_id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在于该知识库中")
    return {"code": 0, "message": "文档移除成功", "data": None}


@router.post("/{kb_id}/quick-questions/generate", response_model=dict)
async def generate_quick_questions(
    kb_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    kb = await knowledge_base_service.get(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if kb.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权限操作此知识库")

    doc_ids = await knowledge_base_service.get_document_ids(db, kb_id)
    if not doc_ids:
        raise HTTPException(status_code=400, detail="知识库中暂无文档，无法生成快捷问题")

    try:
        questions = await knowledge_base_service.generate_quick_questions(
            db=db,
            kb_id=kb_id,
            kb_name=kb.name,
            kb_description=kb.description,
        )
    except Exception as e:
        logger.exception(f"生成快捷问题失败: {e}")
        raise HTTPException(status_code=500, detail="生成快捷问题失败")

    return {
        "code": 0,
        "message": "快捷问题生成成功",
        "data": {"quick_questions": questions},
    }


@router.post("/quick-questions/preview", response_model=dict)
async def preview_quick_questions(
    body: QuickQuestionsPreviewIn,
    current_user: CurrentUser,
):
    questions = await knowledge_base_service.generate_quick_questions_preview(
        name=body.name,
        description=body.description,
    )
    return {
        "code": 0,
        "message": "ok",
        "data": questions,
    }