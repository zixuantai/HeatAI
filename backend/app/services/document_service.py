from __future__ import annotations

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
from app.models.knowledge_base import KnowledgeBaseDocument
from app.services.processing.pipeline import ProcessingPipeline
from app.services.processing.corpus_dedup_service import CorpusDedupService
from app.services.processing.classifier import document_classifier
from app.services.retrieval.bm25_service import bm25_service
from app.services.retrieval.embedding import embedding_service
from app.services.retrieval.reranker_service import reranker_service
from app.services.retrieval.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class DocumentService:

    @staticmethod
    def _exclude_kb_docs():
        return ~Document.id.in_(
            select(KnowledgeBaseDocument.document_id)
        )

    @staticmethod
    async def upload_and_process(
        db: AsyncSession,
        user_id: str,
        file_bytes: bytes,
        original_filename: str,
        org_id: str | None = None,
        knowledge_base_id: str | None = None,
    ) -> Document:
        upload_start = time.time()
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        dedup_conditions = [
            Document.content_hash == content_hash,
            Document.status == "completed",
        ]
        if org_id:
            dedup_conditions.append(Document.organization_id == org_id)
        else:
            dedup_conditions.append(Document.user_id == user_id)
            dedup_conditions.append(Document.organization_id.is_(None))

        result = await db.execute(
            select(Document).where(*dedup_conditions)
        )
        existing = result.scalars().first()
        if existing:
            raise ValueError(
                f"该文件已上传过（内容与「{existing.original_filename}」相同），不能重复上传"
            )

        doc_record = Document(
            user_id=user_id,
            organization_id=org_id,
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

            pipeline = ProcessingPipeline.default()

            try:
                parsed_text, title = pipeline.parser.parse(file_bytes, original_filename)
            except ValueError:
                raise
            except Exception as e:
                ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
                if ext == "pdf":
                    raise ValueError(f"PDF文件无法打开，可能已损坏或不是有效的PDF格式: {e}")
                raise ValueError(f"文件解析失败 ({type(e).__name__}): {e}")
            if not parsed_text or not parsed_text.strip():
                raise ValueError("文档解析结果为空")

            try:
                result = await document_classifier.classify(title, parsed_text)
                category = result.get("category")
                if category:
                    doc_record.category = category
                    await db.commit()
                    await db.refresh(doc_record)
                    logger.info(f"[文档分类] 文档 {original_filename} 分类为: {category} (置信度: {result.get('confidence')})")
                else:
                    logger.info(f"[文档分类] 文档 {original_filename} 未匹配到已知类别: {result.get('reason')}")
            except Exception as class_err:
                logger.warning(f"[文档分类] 分类过程异常，继续处理: {class_err}")

            corpus_dedup = CorpusDedupService(
                threshold=settings.MINHASH_THRESHOLD,
                num_perm=settings.MINHASH_NUM_PERM,
            )
            similar_doc = await corpus_dedup.check_duplicate(
                db, user_id, parsed_text
            )
            if similar_doc:
                raise ValueError(
                    "该文档与已上传的「{name}」内容高度相似，建议检查是否重复上传".format(
                        name=similar_doc.original_filename
                    )
                )

            base_metadata: Dict[str, Any] = {
                "source": original_filename,
                "document_id": doc_record.id,
                "title": title,
            }

            chunks = pipeline.run(
                filename=original_filename,
                base_metadata=base_metadata,
                parsed_text=parsed_text,
                title=title,
            )

            chunk_start = time.time()
            logger.info(f"[文本切块] 切块数量: {len(chunks)}")

            for i, chunk in enumerate(chunks):
                content_len = len(chunk["content"])
                content_preview = chunk["content"][:80].replace("\n", "\\n")
                logger.info(f"[文本切块] 分块 #{i}: 大小={content_len}字符, "
                           f"段落范围=[{chunk['metadata'].get('paragraph_start', '?')}-{chunk['metadata'].get('paragraph_end', '?')}], "
                           f"内容预览={content_preview}...")
            logger.info(f"[文本切块] ✅ 全部 {len(chunks)} 个分块切分成功")

            chunk_texts = [
                f"标题: {c['metadata'].get('title', '')}\n{c['content']}"
                if c['metadata'].get('title') else c['content']
                for c in chunks
            ]

            embed_start = time.time()
            logger.info(f"[向量化] 开始编码 {len(chunk_texts)} 个文本块...")
            embeddings = embedding_service.encode(chunk_texts)
            if not embeddings:
                raise RuntimeError("向量编码结果为空，请检查 Embedding 模型是否正常加载")
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
                milvus_service.insert(chunks, embeddings, org_id=org_id, knowledge_base_id=knowledge_base_id)
                logger.info(f"[Milvus 插入] ✅ 成功插入 {len(chunks)} 条向量, 耗时: {time.time() - insert_start:.2f}s")
            except Exception as e:
                logger.error(f"[Milvus 插入] ❌ 插入失败: {type(e).__name__}: {e}")
                raise

            bm25_start = time.time()
            bm25_service.add_chunks(chunks, org_id=org_id, knowledge_base_id=knowledge_base_id)
            logger.info(f"[BM25 索引] ✅ 已添加 {len(chunks)} 个分块, 耗时: {time.time() - bm25_start:.2f}s")

            doc_record.chunk_count = len(chunks)
            await corpus_dedup.index_signature(db, doc_record.id, parsed_text)
            doc_record.status = "completed"
            await db.commit()
            await db.refresh(doc_record)

            total_time = time.time() - upload_start
            logger.info(f"[文档上传] ✅ 全部处理完成: {original_filename}, "
                       f"分块数={len(chunks)}, 向量维度={vector_dim}, 总耗时={total_time:.2f}s")
            logger.info("=" * 60)

            return doc_record

        except Exception as e:
            logger.exception(f"[文档上传] ❌ 处理失败: {original_filename}, 错误: {type(e).__name__}: {e}")
            doc_record.status = "failed"
            doc_record.error_message = str(e)
            await db.commit()
            await db.refresh(doc_record)

            try:
                deleted_count = milvus_service.delete_by_document_id(doc_record.id)
                if deleted_count > 0:
                    logger.info(f"[回滚] 已清理 Milvus 中 {doc_record.id} 的 {deleted_count} 条向量")
            except Exception as cleanup_err:
                logger.warning(f"[回滚] Milvus 清理失败 ({doc_record.id}): {cleanup_err}")

            try:
                bm25_service.remove_by_document_id(doc_record.id, org_id=org_id, knowledge_base_id=knowledge_base_id)
                logger.info(f"[回滚] 已清理 BM25 中 {doc_record.id} 的索引")
            except Exception as cleanup_err:
                logger.warning(f"[回滚] BM25 清理失败 ({doc_record.id}): {cleanup_err}")

            raise

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        org_id: str | None = None,
    ) -> tuple[list[Document], int]:
        conditions = []
        if org_id:
            conditions.append(Document.organization_id == org_id)
        else:
            conditions.append(Document.user_id == user_id)
            conditions.append(Document.organization_id.is_(None))

        conditions.append(DocumentService._exclude_kb_docs())

        if search:
            conditions.append(Document.original_filename.ilike(f"%{search}%"))

        result = await db.execute(
            select(func.count(Document.id)).where(*conditions)
        )
        total = result.scalar() or 0

        result = await db.execute(
            select(Document)
            .where(*conditions)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        documents = list(result.scalars().all())
        return documents, total

    @staticmethod
    async def list_all_document_ids(
        db: AsyncSession,
        user_id: str,
        search: str | None = None,
        org_id: str | None = None,
    ) -> list[str]:
        conditions = []
        if org_id:
            conditions.append(Document.organization_id == org_id)
        else:
            conditions.append(Document.user_id == user_id)
            conditions.append(Document.organization_id.is_(None))

        conditions.append(DocumentService._exclude_kb_docs())

        if search:
            conditions.append(Document.original_filename.ilike(f"%{search}%"))
        result = await db.execute(
            select(Document.id).where(*conditions).order_by(Document.created_at.desc())
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def get_document(db: AsyncSession, document_id: str, user_id: str, org_id: str | None = None) -> Document | None:
        conditions = [Document.id == document_id]
        if org_id:
            conditions.append(Document.organization_id == org_id)
        else:
            conditions.append(Document.user_id == user_id)
            conditions.append(Document.organization_id.is_(None))

        result = await db.execute(
            select(Document).where(*conditions)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_document(db: AsyncSession, document_id: str, user_id: str, org_id: str | None = None) -> tuple[bool, str | None]:
        document = await DocumentService.get_document(db, document_id, user_id, org_id)
        if not document:
            return False, None

        filename = document.filename

        await db.delete(document)
        await db.commit()

        return True, filename

    @staticmethod
    def cleanup_document_resources(document_id: str, filename: str, org_id: str | None = None):
        try:
            file_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"删除文件失败 [{document_id}]: {e}")

        try:
            milvus_service.delete_by_document_id(document_id)
        except Exception as e:
            logger.warning(f"Milvus 删除失败 [{document_id}]: {e}")

        try:
            bm25_service.remove_by_document_id(document_id, org_id=org_id)
        except Exception as e:
            logger.warning(f"BM25 删除失败 [{document_id}]: {e}")

        logger.info(f"文档 {document_id} 资源清理完成")

    @staticmethod
    async def delete_documents_batch(db: AsyncSession, document_ids: list[str], user_id: str, org_id: str | None = None) -> tuple[int, list[tuple[str, str]]]:
        cleanup_list: list[tuple[str, str]] = []
        deleted_count = 0
        for document_id in document_ids:
            document = await DocumentService.get_document(db, document_id, user_id, org_id)
            if not document:
                continue

            filename = document.filename
            cleanup_list.append((document_id, filename))

            await db.delete(document)
            deleted_count += 1

        await db.commit()
        return deleted_count, cleanup_list

    @staticmethod
    def cleanup_documents_batch(cleanup_list: list[tuple[str, str]], org_id: str | None = None):
        for document_id, filename in cleanup_list:
            try:
                file_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"删除文件失败 [{document_id}]: {e}")

            try:
                milvus_service.delete_by_document_id(document_id)
            except Exception as e:
                logger.warning(f"Milvus 删除失败 [{document_id}]: {e}")

        bm25_removed_ids = [did for did, _ in cleanup_list]
        try:
            bm25_service.remove_by_document_ids(bm25_removed_ids, org_id=org_id)
        except Exception as e:
            logger.warning(f"BM25 批量删除失败: {e}")

        logger.info(f"批量清理完成: {len(cleanup_list)} 个文档")

    @staticmethod
    async def get_stats(
        db: AsyncSession,
        user_id: str,
        org_id: str | None = None,
    ) -> dict:
        from sqlalchemy import case

        conditions = []
        if org_id:
            conditions.append(Document.organization_id == org_id)
        else:
            conditions.append(Document.user_id == user_id)
            conditions.append(Document.organization_id.is_(None))

        conditions.append(DocumentService._exclude_kb_docs())

        result = await db.execute(
            select(func.count(Document.id)).where(*conditions)
        )
        total = result.scalar() or 0

        result = await db.execute(
            select(Document.file_type, func.count(Document.id))
            .where(*conditions)
            .group_by(Document.file_type)
            .order_by(func.count(Document.id).desc())
        )
        by_file_type = [{"type": row[0], "count": row[1]} for row in result.all()]

        result = await db.execute(
            select(
                Document.category,
                func.count(Document.id).label("count"),
            )
            .where(*conditions)
            .group_by(Document.category)
            .order_by(func.count(Document.id).desc())
        )
        by_category = [{"category": row[0] or "未分类", "count": row[1]} for row in result.all()]

        return {
            "total": total,
            "by_file_type": by_file_type,
            "by_category": by_category,
        }

    @staticmethod
    async def get_chunks(db: AsyncSession, document_id: str, user_id: str, org_id: str | None = None) -> List[Dict[str, Any]]:
        document = await DocumentService.get_document(db, document_id, user_id, org_id)
        if not document:
            return []
        return milvus_service.get_document_chunks(document_id)

    @staticmethod
    async def search(query: str, top_k: int = 5, org_id: str | None = None) -> List[Dict[str, Any]]:
        return reranker_service.search_and_rerank(query, top_k=top_k, org_id=org_id)

    @staticmethod
    async def rerank_search(
        query: str,
        top_k: int = 5,
        bm25_weight: float | None = None,
        bge_weight: float | None = None,
        org_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        return reranker_service.search_and_rerank(
            query=query,
            top_k=top_k,
            bm25_weight=bm25_weight,
            bge_weight=bge_weight,
            org_id=org_id,
        )


document_service = DocumentService()
