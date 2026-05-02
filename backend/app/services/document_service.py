import os
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
from app.services.embedding import embedding_service
from app.services.milvus_service import milvus_service


class DocumentService:

    @staticmethod
    async def upload_and_process(
        db: AsyncSession,
        user_id: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> Document:
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

        try:
            doc_record.filename = f"{doc_record.id}.{doc_record.file_type}"
            await db.commit()
            await db.refresh(doc_record)

            upload_dir = os.path.abspath(settings.UPLOAD_DIR)
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, doc_record.filename)
            with open(file_path, "wb") as f:
                f.write(file_bytes)

            parsed_text, title = document_parser.parse(file_bytes, original_filename)
            if not parsed_text or not parsed_text.strip():
                raise ValueError("文档解析结果为空")

            cleaned_text = text_cleaner.clean(parsed_text)
            if not cleaned_text or not cleaned_text.strip():
                raise ValueError("文本清洗后为空")

            base_metadata: Dict[str, Any] = {
                "source": original_filename,
                "title": title,
                "document_id": doc_record.id,
            }
            chunks = text_chunker.chunk(cleaned_text, base_metadata)

            if not chunks:
                raise ValueError("文本切块结果为空")

            chunk_texts = [c["content"] for c in chunks]
            embeddings = embedding_service.encode(chunk_texts)

            for i, chunk in enumerate(chunks):
                chunk["metadata"]["chunk_id"] = str(uuid.uuid4())

            milvus_service.insert(chunks, embeddings)

            doc_record.chunk_count = len(chunks)
            doc_record.status = "completed"
            await db.commit()
            await db.refresh(doc_record)

            return doc_record

        except Exception as e:
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
        query_embedding = embedding_service.encode_single(query)
        return milvus_service.search(query_embedding, top_k=top_k)


document_service = DocumentService()
