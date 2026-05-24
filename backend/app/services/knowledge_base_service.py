import logging
import json
import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.knowledge_base import (
    KnowledgeBase, KnowledgeBaseDocument, KnowledgeBaseLike, KnowledgeBaseFavorite, KnowledgeBaseMember
)
from app.models.document import Document
from app.services.retrieval.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class KnowledgeBaseService:

    @staticmethod
    async def create(
        db: AsyncSession,
        owner_id: str,
        owner_name: str | None,
        name: str,
        description: str | None = None,
        avatar: str | None = None,
        cover_color: str | None = None,
        quick_questions: list[str] | None = None,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            name=name,
            description=description,
            avatar=avatar,
            cover_color=cover_color,
            owner_id=owner_id,
            owner_name=owner_name,
        )
        if quick_questions:
            kb.quick_questions = quick_questions[:4]
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        return kb

    @staticmethod
    async def get(db: AsyncSession, kb_id: str) -> KnowledgeBase | None:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.status == "active",
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_bases(
        db: AsyncSession,
        user_id: str | None = None,
        search: str | None = None,
        sort_by: str = "latest",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[KnowledgeBase], int]:
        from app.services.knowledge_base_listing import list_bases as listing_list_bases
        return await listing_list_bases(db, user_id, search, sort_by, limit, offset)

    @staticmethod
    async def update(
        db: AsyncSession,
        kb_id: str,
        owner_id: str,
        name: str | None = None,
        description: str | None = None,
        avatar: str | None = None,
        cover_color: str | None = None,
        quick_questions: list[str] | None = None,
        is_recommended: bool | None = None,
    ) -> KnowledgeBase | None:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.owner_id == owner_id,
                KnowledgeBase.status == "active",
            )
        )
        kb = result.scalar_one_or_none()
        if not kb:
            return None

        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        if avatar is not None:
            kb.avatar = avatar
        if cover_color is not None:
            kb.cover_color = cover_color
        if quick_questions is not None:
            kb.quick_questions = quick_questions[:4]
        if is_recommended is not None:
            kb.is_recommended = is_recommended

        await db.commit()
        await db.refresh(kb)
        return kb

    @staticmethod
    async def delete(db: AsyncSession, kb_id: str, owner_id: str) -> bool:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.owner_id == owner_id,
                KnowledgeBase.status == "active",
            )
        )
        kb = result.scalar_one_or_none()
        if not kb:
            return False

        kb.status = "deleted"
        await db.commit()
        return True

    @staticmethod
    async def increment_view(db: AsyncSession, kb_id: str) -> None:
        result = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.status == "active",
            )
        )
        kb = result.scalar_one_or_none()
        if kb:
            kb.view_count += 1
            await db.commit()

    @staticmethod
    async def toggle_like(db: AsyncSession, kb_id: str, user_id: str) -> bool:
        result = await db.execute(
            select(KnowledgeBaseLike).where(
                KnowledgeBaseLike.knowledge_base_id == kb_id,
                KnowledgeBaseLike.user_id == user_id,
            )
        )
        like = result.scalar_one_or_none()

        if like:
            await db.delete(like)
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if kb and kb.like_count > 0:
                kb.like_count -= 1
            await db.commit()
            return False
        else:
            like = KnowledgeBaseLike(
                knowledge_base_id=kb_id,
                user_id=user_id,
            )
            db.add(like)
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if kb:
                kb.like_count += 1
            await db.commit()
            return True

    @staticmethod
    async def toggle_favorite(db: AsyncSession, kb_id: str, user_id: str) -> bool:
        result = await db.execute(
            select(KnowledgeBaseFavorite).where(
                KnowledgeBaseFavorite.knowledge_base_id == kb_id,
                KnowledgeBaseFavorite.user_id == user_id,
            )
        )
        favorite = result.scalar_one_or_none()

        if favorite:
            await db.delete(favorite)
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if kb and kb.favorite_count > 0:
                kb.favorite_count -= 1
            await db.commit()
            return False
        else:
            favorite = KnowledgeBaseFavorite(
                knowledge_base_id=kb_id,
                user_id=user_id,
            )
            db.add(favorite)
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            kb = kb_result.scalar_one_or_none()
            if kb:
                kb.favorite_count += 1
            await db.commit()
            return True

    @staticmethod
    async def get_user_interactions(
        db: AsyncSession, kb_id: str, user_id: str
    ) -> dict[str, bool]:
        like_result = await db.execute(
            select(KnowledgeBaseLike).where(
                KnowledgeBaseLike.knowledge_base_id == kb_id,
                KnowledgeBaseLike.user_id == user_id,
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None

        favorite_result = await db.execute(
            select(KnowledgeBaseFavorite).where(
                KnowledgeBaseFavorite.knowledge_base_id == kb_id,
                KnowledgeBaseFavorite.user_id == user_id,
            )
        )
        is_favorited = favorite_result.scalar_one_or_none() is not None

        return {"is_liked": is_liked, "is_favorited": is_favorited}

    @staticmethod
    async def get_user_member_info(
        db: AsyncSession, kb_id: str, user_id: str
    ) -> dict[str, bool]:
        member_result = await db.execute(
            select(KnowledgeBaseMember).where(
                KnowledgeBaseMember.knowledge_base_id == kb_id,
                KnowledgeBaseMember.user_id == user_id,
            )
        )
        return {"is_joined": member_result.scalar_one_or_none() is not None}

    @staticmethod
    async def toggle_join(
        db: AsyncSession, kb_id: str, user_id: str
    ) -> tuple[bool, int]:
        result = await db.execute(
            select(KnowledgeBaseMember).where(
                KnowledgeBaseMember.knowledge_base_id == kb_id,
                KnowledgeBaseMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()

        if member:
            await db.delete(member)
            await db.commit()
            count_result = await db.execute(
                select(func.count(KnowledgeBaseMember.id)).where(
                    KnowledgeBaseMember.knowledge_base_id == kb_id
                )
            )
            return False, count_result.scalar() or 0
        else:
            member = KnowledgeBaseMember(
                knowledge_base_id=kb_id,
                user_id=user_id,
            )
            db.add(member)
            await db.commit()
            count_result = await db.execute(
                select(func.count(KnowledgeBaseMember.id)).where(
                    KnowledgeBaseMember.knowledge_base_id == kb_id
                )
            )
            return True, count_result.scalar() or 0

    @staticmethod
    async def list_member_ids(
        db: AsyncSession, kb_id: str
    ) -> list[str]:
        result = await db.execute(
            select(KnowledgeBaseMember.user_id).where(
                KnowledgeBaseMember.knowledge_base_id == kb_id
            )
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def count_user_kb_messages(
        db: AsyncSession, kb_id: str, user_id: str
    ) -> int:
        from app.models.conversation import Message
        result = await db.execute(
            select(func.count(Message.id)).join(
                Message.session
            ).where(
                Message.session.has(knowledge_base_id=kb_id),
                Message.role == "user",
                Message.session.has(user_id=user_id),
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def add_document(
        db: AsyncSession, kb_id: str, document_id: str
    ) -> KnowledgeBaseDocument:
        existing_result = await db.execute(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.knowledge_base_id == kb_id,
                KnowledgeBaseDocument.document_id == document_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return existing

        link = KnowledgeBaseDocument(
            knowledge_base_id=kb_id,
            document_id=document_id,
        )
        db.add(link)

        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        if kb:
            kb.doc_count += 1

        await db.commit()
        await db.refresh(link)
        return link

    @staticmethod
    async def remove_document(
        db: AsyncSession, kb_id: str, document_id: str
    ) -> bool:
        result = await db.execute(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.knowledge_base_id == kb_id,
                KnowledgeBaseDocument.document_id == document_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            return False

        await db.delete(link)

        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        if kb and kb.doc_count > 0:
            kb.doc_count -= 1

        await db.commit()
        return True

    @staticmethod
    async def list_documents(
        db: AsyncSession, kb_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[Document], int]:
        count_result = await db.execute(
            select(func.count(KnowledgeBaseDocument.id)).where(
                KnowledgeBaseDocument.knowledge_base_id == kb_id
            )
        )
        total = count_result.scalar() or 0

        links_result = await db.execute(
            select(KnowledgeBaseDocument)
            .where(KnowledgeBaseDocument.knowledge_base_id == kb_id)
            .order_by(KnowledgeBaseDocument.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        links = list(links_result.scalars().all())

        if not links:
            return [], total

        doc_ids = [link.document_id for link in links]
        docs_result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids))
        )
        docs = {doc.id: doc for doc in docs_result.scalars().all()}

        ordered_docs = [docs[link.document_id] for link in links if link.document_id in docs]
        return ordered_docs, total

    @staticmethod
    async def get_document_ids(db: AsyncSession, kb_id: str) -> list[str]:
        result = await db.execute(
            select(KnowledgeBaseDocument.document_id).where(
                KnowledgeBaseDocument.knowledge_base_id == kb_id
            )
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def generate_quick_questions(
        db: AsyncSession,
        kb_id: str,
        kb_name: str,
        kb_description: str | None,
    ) -> list[str]:
        doc_ids = await KnowledgeBaseService.get_document_ids(db, kb_id)
        if not doc_ids:
            return []

        chunks = []
        for doc_id in doc_ids[:5]:
            doc_chunks = milvus_service.get_document_chunks(doc_id)
            for c in doc_chunks[:2]:
                chunks.append(c.get("content", "")[:500])

        chunks_summary = "\n---\n".join(chunks)[:2000]
        if not chunks_summary.strip():
            return []

        prompt = f"""你是一个专业的知识库问题生成器。根据以下知识库文档内容，生成4个用户最可能提问的快捷问题。

要求：
1. 问题应覆盖文档的不同方面，不要重复
2. 问题应简洁自然，像真实用户会问的问题
3. 每个问题不超过20个字
4. 问题应与文档内容直接相关
5. 直接返回4个问题，每行一个，不要编号、不要解释

知识库名称：{kb_name}
知识库简介：{kb_description or '暂无'}

文档内容摘要：
{chunks_summary}

请生成4个快捷问题："""

        try:
            from app.services.chat.service import ChatService
            from app.services.chat.engine.response_parser import extract_content

            response = await ChatService._call_model(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                enable_tools=False,
            )

            if response.status_code == 200:
                content = extract_content(response).strip()
                questions = [q.strip().strip("0123456789.、）)）") for q in content.split("\n") if q.strip()]
                questions = [q for q in questions if len(q) > 2]
                questions = questions[:4]

                kb = await KnowledgeBaseService.get(db, kb_id)
                if kb and questions:
                    kb.quick_questions = questions
                    await db.commit()

                return questions
        except Exception as e:
            logger.warning(f"[快捷问题生成] LLM调用失败: {e}")

        return []

    @staticmethod
    async def generate_quick_questions_preview(
        name: str,
        description: str | None,
    ) -> list[str]:
        prompt = f"""你是一个专业的知识库问题生成器。根据知识库的名称和简介，生成4个用户最可能提问的快捷问题。

要求：
1. 问题应覆盖知识库可能涉及的不同方面，不要重复
2. 问题应简洁自然，像真实用户会问的问题
3. 每个问题不超过20个字
4. 问题应与知识库主题直接相关
5. 直接返回4个问题，每行一个，不要编号、不要解释

知识库名称：{name}
知识库简介：{description or '暂无'}

请生成4个快捷问题："""

        try:
            from app.services.chat.service import ChatService
            from app.services.chat.engine.response_parser import extract_content

            response = await ChatService._call_model(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                enable_tools=False,
            )

            if response.status_code == 200:
                content = extract_content(response).strip()
                questions = [q.strip() for q in content.split("\n") if q.strip()]
                questions = [q.lstrip("0123456789.、)） ") for q in questions]
                questions = [q for q in questions if len(q) >= 2]
                questions = questions[:4]

                return questions
        except Exception as e:
            logger.warning(f"[快捷问题预览生成] LLM调用失败: {e}")

        return []


knowledge_base_service = KnowledgeBaseService()