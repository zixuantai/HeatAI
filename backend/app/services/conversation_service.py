from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.conversation import ConversationSession, Message
from app.services.memory.short_term import short_term_memory
from app.services.memory.long_term import long_term_memory


class ConversationService:

    @staticmethod
    async def create_session(db: AsyncSession, user_id: str, title: str = "新对话") -> ConversationSession:
        session = ConversationSession(user_id=user_id, title=title)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        short_term_memory.create_session(session.id)
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
            select(ConversationSession).where(
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
            .order_by(ConversationSession.updated_at.desc())
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
        user_messages = [
            t.content for t in short_term_memory.get_recent_turns(session_id)
            if t.role == "user"
        ]
        if not user_messages:
            return
        existing = await long_term_memory.load(db, user_id)
        new_prefs = long_term_memory.extract_from_messages(user_messages, existing)
        await long_term_memory.save(db, user_id, new_prefs)


conversation_service = ConversationService()
