from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.memory.short_term import short_term_memory
from app.services.memory.long_term import long_term_memory


@dataclass
class Context:
    messages: list[dict] = field(default_factory=list)
    has_long_term: bool = False
    has_short_term: bool = False


class ContextBuilder:

    @staticmethod
    async def build(
        db: AsyncSession,
        session_id: str,
        user_id: str,
        current_message: str,
        round_count: int = 10
    ) -> Context:
        context = Context()

        long_term_text = await long_term_memory.get_context_text(db, user_id)
        if long_term_text:
            context.messages.append({
                "role": "system",
                "content": f"[用户长期记忆]\n{long_term_text}"
            })
            context.has_long_term = True

        if not short_term_memory.has_session(session_id):
            await short_term_memory.load_from_db(db, session_id, round_count * 2)

        recent_turns = short_term_memory.get_recent_as_messages(session_id, round_count * 2)
        if recent_turns:
            context.has_short_term = True
            context.messages.extend(recent_turns)

        context.messages.append({"role": "user", "content": current_message})

        return context

    @staticmethod
    async def build_stream_context(
        db: AsyncSession,
        session_id: str,
        user_id: str,
        current_message: str,
        round_count: int = 10
    ) -> Context:
        return await ContextBuilder.build(db, session_id, user_id, current_message, round_count)


context_builder = ContextBuilder()
