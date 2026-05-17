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
    RerankRequest,
    RerankResult,
    ChunkInfo,
    BatchDeleteRequest,
)
from app.services.document_service import document_service
from app.services.processing.parser import DocumentParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档管理"])

MAX_FILE_SIZE = 50 * 1024 * 1024
SUPPORTED_TYPES = tuple(DocumentParser.SUPPORTED_TYPES)


@router.post("/upload", response_model=DocumentInfo, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_TYPES:
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
    except RuntimeError as e:
        error_msg = str(e)
        logger.exception(f"文档上传运行时异常: {file.filename} - {error_msg}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {error_msg}")
    except TimeoutError as e:
        logger.exception(f"文档上传超时: {file.filename}")
        raise HTTPException(status_code=504, detail="文档处理超时，请检查后端服务(Milvus/Embedding)是否正常运行")
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"文档上传处理异常: {file.filename} - {error_msg}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {error_msg}")

    return document


@router.get("", response_model=dict)
async def list_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
):
    documents, total = await document_service.list_documents(
        db=db,
        user_id=str(current_user.id),
        limit=limit,
        offset=offset,
        search=search,
    )
    items = []
    for doc in documents:
        try:
            items.append(DocumentInfo.model_validate(doc).model_dump(mode="json"))
        except Exception:
            logger.exception(f"文档记录验证失败，ID={doc.id}，状态={doc.status}")
            items.append({
                "id": doc.id,
                "filename": getattr(doc, "filename", ""),
                "original_filename": getattr(doc, "original_filename", "未知"),
                "file_type": getattr(doc, "file_type", "unknown"),
                "file_size": getattr(doc, "file_size", 0),
                "chunk_count": getattr(doc, "chunk_count", 0),
                "status": getattr(doc, "status", "failed"),
                "error_message": str(e)[:200],
                "created_at": getattr(doc, "created_at", None),
                "updated_at": getattr(doc, "updated_at", None),
            })
    return {
        "code": 0,
        "message": "success",
        "data": {"total": total, "items": items},
    }


@router.delete("/batch")
async def delete_documents_batch(
    body: BatchDeleteRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    deleted_count, cleanup_list = await document_service.delete_documents_batch(db, body.ids, str(current_user.id))
    if cleanup_list:
        document_service.cleanup_documents_batch(cleanup_list)
    return {"code": 0, "message": f"已删除 {deleted_count} 个文档", "data": {"deleted_count": deleted_count}}


@router.get("/ids")
async def list_all_document_ids(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=200),
):
    ids = await document_service.list_all_document_ids(
        db=db,
        user_id=str(current_user.id),
        search=search,
    )
    return {"code": 0, "message": "success", "data": {"ids": ids, "total": len(ids)}}


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


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    success, filename = await document_service.delete_document(db, document_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    if filename:
        document_service.cleanup_document_resources(document_id, filename)
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


@router.post("/rerank", response_model=dict)
async def rerank_documents(
    body: RerankRequest,
    current_user: CurrentUser,
):
    results = await document_service.rerank_search(
        query=body.query,
        top_k=body.top_k,
        bm25_weight=body.bm25_weight,
        bge_weight=body.bge_weight,
    )
    rerank_results = [RerankResult(**r).model_dump(mode="json") for r in results]
    return {
        "code": 0,
        "message": "success",
        "data": {"query": body.query, "results": rerank_results},
    }
