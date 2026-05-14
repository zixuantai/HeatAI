import asyncio
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.conversation import ConversationSession, Message
from app.services.memory.short_term import short_term_memory
from app.services.memory.long_term import long_term_memory

logger = logging.getLogger(__name__)


class ConversationService:

    @staticmethod
    async def create_session(db: AsyncSession, user_id: str, title: str = "新对话") -> ConversationSession:
        session = ConversationSession(user_id=user_id, title=title)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        short_term_memory.create_session(session.id)

        asyncio.ensure_future(long_term_memory.merge_sessions(db, user_id))

        return session

    @staticmethod
    async def get_session(db: AsyncSession, session_id: str, user_id: str) -> ConversationSession | None:
        result = await db.execute(
            select(ConversationSession).where(
                ConversationSession.id == session_id,
                ConversationSession.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_session_with_messages(db: AsyncSession, session_id: str, user_id: str) -> ConversationSession | None:
        result = await db.execute(
            select(ConversationSession)
            .options(selectinload(ConversationSession.messages))
            .where(
                ConversationSession.id == session_id,
                ConversationSession.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_sessions(db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0) -> list[ConversationSession]:
        result = await db.execute(
            select(ConversationSession)
            .where(ConversationSession.user_id == user_id)
            .order_by(ConversationSession.is_pinned.desc(), ConversationSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def save_message(db: AsyncSession, session_id: str, role: str, content: str) -> Message:
        message = Message(session_id=session_id, role=role, content=content)
        db.add(message)
        await db.execute(
            update(ConversationSession)
            .where(ConversationSession.id == session_id)
            .values(message_count=ConversationSession.message_count + 1)
        )
        await db.commit()
        await db.refresh(message)

        if role == "user":
            session = await db.get(ConversationSession, session_id)
            if session and session.title == "新对话":
                title = content[:30] + ("..." if len(content) > 30 else "")
                session.title = title
                await db.commit()
                asyncio.ensure_future(ConversationService._auto_generate_title(session_id, content))

        short_term_memory.add_turn(session_id, role, content)
        return message

    @staticmethod
    async def get_messages(db: AsyncSession, session_id: str, limit: int = 100) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_session_title(db: AsyncSession, session_id: str, user_id: str, title: str) -> ConversationSession | None:
        session = await ConversationService.get_session(db, session_id, user_id)
        if not session:
            return None
        session.title = title
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def toggle_pin(db: AsyncSession, session_id: str, user_id: str, is_pinned: bool) -> ConversationSession | None:
        session = await ConversationService.get_session(db, session_id, user_id)
        if not session:
            return None
        session.is_pinned = is_pinned
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: str, user_id: str) -> bool:
        session = await ConversationService.get_session(db, session_id, user_id)
        if not session:
            return False
        await db.delete(session)
        await db.commit()
        short_term_memory.remove_session(session_id)
        return True

    @staticmethod
    async def ensure_session_loaded(db: AsyncSession, session_id: str) -> None:
        if not short_term_memory.has_session(session_id):
            await short_term_memory.load_from_db(db, session_id)

    @staticmethod
    async def extract_and_save_long_term(db: AsyncSession, user_id: str, session_id: str) -> None:
        turns = short_term_memory.get_recent_turns(session_id)
        user_messages = [t.content for t in turns if t.role == "user"]
        assistant_messages = [t.content for t in turns if t.role == "assistant"]
        if not user_messages:
            return
        await long_term_memory.extract_and_save(
            db=db,
            user_id=user_id,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
        )
        await long_term_memory.finalize_session(
            db=db,
            user_id=user_id,
            session_id=session_id,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
        )

    @staticmethod
    async def _auto_generate_title(session_id: str, user_message: str) -> None:
        try:
            title = await ConversationService._generate_title_via_llm(user_message)
            from app.core.database import async_session
            async with async_session() as db:
                session = await db.get(ConversationSession, session_id)
                if session:
                    session.title = title
                    await db.commit()
                    logger.info(f"[会话标题] 智能生成: '{title}' (会话: {session_id})")
        except Exception as e:
            logger.warning(f"[会话标题] 智能生成失败，保留默认标题: {e}")

    @staticmethod
    async def _generate_title_via_llm(user_message: str) -> str:
        from app.services.chat import ChatService, extract_content
        from app.core.config import settings

        prompt = f"""根据以下用户问题，生成一个简洁的对话标题（10个字以内），直接返回标题文本，不要包含引号、标点或任何额外解释。

用户问题：{user_message}

标题："""

        response = await ChatService._call_model(
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            enable_tools=False
        )

        if response.status_code == 200:
            title = extract_content(response).strip()
            title = title.strip('"\'""''「」《》【】[]() （）\n\r\t ,.，。！!？?：:；;、')
            if title:
                return title[:30]
        return user_message[:30]


conversation_service = ConversationService()