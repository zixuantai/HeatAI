import logging
import os
import time
import uuid
import hashlib
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.models.document import Document
from app.services.parser import document_parser
from app.services.text_cleaner import text_cleaner
from app.services.chunker import text_chunker
from app.services.bm25_service import bm25_service
from app.services.embedding import embedding_service
from app.services.hybrid_service import hybrid_service
from app.services.reranker_service import reranker_service
from app.services.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class DocumentService:

    @staticmethod
    async def upload_and_process(
        db: AsyncSession,
        user_id: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> Document:
        upload_start = time.time()
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.content_hash == content_hash,
                Document.status == "completed",
            )
        )
        existing = result.scalars().first()
        if existing:
            raise ValueError("该文件已上传过，内容相同的文件不能重复上传")

        doc_record = Document(
            user_id=user_id,
            filename="",
            original_filename=original_filename,
            file_type=original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "unknown",
            file_size=len(file_bytes),
            content_hash=content_hash,
            status="processing",
        )
        db.add(doc_record)
        await db.commit()
        await db.refresh(doc_record)

        file_size_kb = len(file_bytes) / 1024
        logger.info("=" * 60)
        logger.info(f"[文档上传] 文件名: {original_filename}")
        logger.info(f"[文档上传] 文件大小: {file_size_kb:.2f} KB ({len(file_bytes)} 字节)")
        logger.info(f"[文档上传] 上传时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[文档上传] 文档 ID: {doc_record.id}")

        try:
            doc_record.filename = f"{doc_record.id}.{doc_record.file_type}"
            await db.commit()
            await db.refresh(doc_record)

            upload_dir = os.path.abspath(settings.UPLOAD_DIR)
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, doc_record.filename)
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            logger.info(f"[文档上传] 文件已保存至: {file_path}")

            parse_start = time.time()
            parsed_text, title = document_parser.parse(file_bytes, original_filename)
            if not parsed_text or not parsed_text.strip():
                raise ValueError("文档解析结果为空")
            logger.info(f"[文档解析] 标题: {title}, 文本长度: {len(parsed_text)} 字符, 耗时: {time.time() - parse_start:.2f}s")

            cleaned_text = text_cleaner.clean(parsed_text)
            if not cleaned_text or not cleaned_text.strip():
                raise ValueError("文本清洗后为空")
            logger.info(f"[文本清洗] 清洗后文本长度: {len(cleaned_text)} 字符")

            base_metadata: Dict[str, Any] = {
                "source": original_filename,
                "title": title,
                "document_id": doc_record.id,
            }

            chunk_start = time.time()
            chunks = text_chunker.chunk(cleaned_text, base_metadata)
            logger.info(f"[文本切块] 切块数量: {len(chunks)}, 耗时: {time.time() - chunk_start:.2f}s")

            if not chunks:
                raise ValueError("文本切块结果为空")

            for i, chunk in enumerate(chunks):
                content_len = len(chunk["content"])
                content_preview = chunk["content"][:80].replace("\n", "\\n")
                logger.info(f"[文本切块] 分块 #{i}: 大小={content_len}字符, "
                           f"段落范围=[{chunk['metadata'].get('paragraph_start', '?')}-{chunk['metadata'].get('paragraph_end', '?')}], "
                           f"内容预览={content_preview}...")
            logger.info(f"[文本切块] ✅ 全部 {len(chunks)} 个分块切分成功")

            chunk_texts = [c["content"] for c in chunks]

            embed_start = time.time()
            logger.info(f"[向量化] 开始编码 {len(chunk_texts)} 个文本块...")
            embeddings = embedding_service.encode(chunk_texts)
            embed_time = time.time() - embed_start
            vector_dim = len(embeddings[0]) if embeddings else 0
            logger.info(f"[向量化] ✅ 编码完成: 向量维度={vector_dim}, 数量={len(embeddings)}, 耗时={embed_time:.2f}s")
            for i, emb in enumerate(embeddings):
                emb_preview = emb[:5]
                logger.debug(f"[向量化] 分块 #{i}: 向量维度={len(emb)}, 前5维={[round(v, 6) for v in emb_preview]}")

            for i, chunk in enumerate(chunks):
                chunk["metadata"]["chunk_id"] = str(uuid.uuid4())

            insert_start = time.time()
            logger.info(f"[Milvus 插入] 准备插入 {len(chunks)} 条向量...")
            for i, chunk in enumerate(chunks):
                chunk_id = chunk["metadata"].get("chunk_id", "")
                doc_id = chunk["metadata"].get("document_id", "")
                logger.info(f"[Milvus 插入] 分块 #{i}: chunk_id={chunk_id}, document_id={doc_id}, "
                           f"content_size={len(chunk['content'])}字符")
            try:
                milvus_service.insert(chunks, embeddings)
                logger.info(f"[Milvus 插入] ✅ 成功插入 {len(chunks)} 条向量, 耗时: {time.time() - insert_start:.2f}s")
            except Exception as e:
                logger.error(f"[Milvus 插入] ❌ 插入失败: {type(e).__name__}: {e}")
                raise

            bm25_start = time.time()
            bm25_service.add_chunks(chunks)
            logger.info(f"[BM25 索引] ✅ 已添加 {len(chunks)} 个分块, 耗时: {time.time() - bm25_start:.2f}s")

            doc_record.chunk_count = len(chunks)
            doc_record.status = "completed"
            await db.commit()
            await db.refresh(doc_record)

            total_time = time.time() - upload_start
            logger.info(f"[文档上传] ✅ 全部处理完成: {original_filename}, "
                       f"分块数={len(chunks)}, 向量维度={vector_dim}, 总耗时={total_time:.2f}s")
            logger.info("=" * 60)

            return doc_record

        except Exception as e:
            logger.error(f"[文档上传] ❌ 处理失败: {original_filename}, 错误: {type(e).__name__}: {e}")
            doc_record.status = "failed"
            doc_record.error_message = str(e)
            await db.commit()
            await db.refresh(doc_record)
            raise

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        result = await db.execute(
            select(func.count(Document.id)).where(Document.user_id == user_id)
        )
        total = result.scalar() or 0

        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        documents = list(result.scalars().all())
        return documents, total

    @staticmethod
    async def get_document(db: AsyncSession, document_id: str, user_id: str) -> Document | None:
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_document(db: AsyncSession, document_id: str, user_id: str) -> bool:
        document = await DocumentService.get_document(db, document_id, user_id)
        if not document:
            return False

        file_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        milvus_service.delete_by_document_id(document_id)
        bm25_service.remove_by_document_id(document_id)

        await db.delete(document)
        await db.commit()
        return True

    @staticmethod
    async def get_chunks(db: AsyncSession, document_id: str, user_id: str) -> List[Dict[str, Any]]:
        document = await DocumentService.get_document(db, document_id, user_id)
        if not document:
            return []
        return milvus_service.get_document_chunks(document_id)

    @staticmethod
    async def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return hybrid_service.search(query, top_k=top_k)

    @staticmethod
    async def rerank_search(
        query: str,
        top_k: int = 5,
        bm25_weight: float | None = None,
        bge_weight: float | None = None,
    ) -> List[Dict[str, Any]]:
        return reranker_service.search_and_rerank(
            query=query,
            top_k=top_k,
            bm25_weight=bm25_weight,
            bge_weight=bge_weight,
        )


document_service = DocumentService()
