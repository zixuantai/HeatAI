import logging
from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.document import (
    DocumentInfo,
    SearchRequest,
    SearchResult,
    ChunkInfo,
)
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档管理"])

MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=DocumentInfo, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("pdf", "docx", "doc", "html", "htm", "txt"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: .{ext}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="文件不能为空")

    try:
        document = await document_service.upload_and_process(
            db=db,
            user_id=str(current_user.id),
            file_bytes=file_bytes,
            original_filename=file.filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"文档上传处理异常: {file.filename}")
        raise HTTPException(status_code=500, detail="文档处理失败，请稍后重试")

    return document


@router.get("", response_model=dict)
async def list_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    documents, total = await document_service.list_documents(
        db=db,
        user_id=str(current_user.id),
        limit=limit,
        offset=offset,
    )
    items = []
    for doc in documents:
        try:
            items.append(DocumentInfo.model_validate(doc).model_dump(mode="json"))
        except Exception:
            logger.exception(f"文档记录验证失败: {doc.id}")
            total -= 1
    return {
        "code": 0,
        "message": "success",
        "data": {"total": total, "items": items},
    }


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    document = await document_service.get_document(db, document_id, str(current_user.id))
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {
        "code": 0,
        "message": "success",
        "data": DocumentInfo.model_validate(document).model_dump(mode="json"),
    }


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    success = await document_service.delete_document(db, document_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"code": 0, "message": "文档已删除", "data": None}


@router.get("/{document_id}/chunks", response_model=dict)
async def get_document_chunks(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    document = await document_service.get_document(db, document_id, str(current_user.id))
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    chunks = await document_service.get_chunks(db, document_id, str(current_user.id))
    chunk_infos = [
        ChunkInfo(
            id=c.get("id", ""),
            content=c.get("content", ""),
            chunk_index=c.get("chunk_index", 0),
            title=c.get("title", ""),
            source=c.get("source", ""),
        ).model_dump(mode="json")
        for c in chunks
    ]
    return {
        "code": 0,
        "message": "success",
        "data": {
            "document": DocumentInfo.model_validate(document).model_dump(mode="json"),
            "chunks": chunk_infos,
        },
    }


@router.post("/search", response_model=dict)
async def search_documents(
    body: SearchRequest,
    current_user: CurrentUser,
):
    results = await document_service.search(body.query, body.top_k)
    search_results = [SearchResult(**r).model_dump(mode="json") for r in results]
    return {
        "code": 0,
        "message": "success",
        "data": {"query": body.query, "results": search_results},
    }
