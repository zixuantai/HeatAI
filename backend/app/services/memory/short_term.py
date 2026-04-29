import time
from collections import deque
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Message

MAX_ROUNDS = 10


@dataclass
class Turn:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class ShortTermMemory:

    def __init__(self, max_rounds: int = MAX_ROUNDS):
        self._store: dict[str, deque[Turn]] = {}
        self._max_rounds = max_rounds

    def create_session(self, session_id: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = deque(maxlen=self._max_rounds * 2)

    def remove_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def has_session(self, session_id: str) -> bool:
        return session_id in self._store

    async def load_from_db(self, db: AsyncSession, session_id: str, count: int | None = None) -> None:
        limit = count if count is not None else self._max_rounds * 2
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        turns = deque(maxlen=self._max_rounds * 2)
        for msg in result.scalars().all():
            turns.append(Turn(role=msg.role, content=msg.content))
        self._store[session_id] = turns

    def add_turn(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = deque(maxlen=self._max_rounds * 2)
        self._store[session_id].append(Turn(role=role, content=content))

    def get_recent_turns(self, session_id: str, count: int | None = None) -> list[Turn]:
        limit = count if count is not None else self._max_rounds * 2
        dq = self._store.get(session_id)
        if not dq:
            return []
        items = list(dq)
        return items[-limit:]

    def get_recent_as_messages(self, session_id: str, count: int | None = None) -> list[dict]:
        return [t.to_dict() for t in self.get_recent_turns(session_id, count)]

    def get_turn_count(self, session_id: str) -> int:
        dq = self._store.get(session_id)
        return len(dq) if dq else 0

    def clear_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def cleanup_expired(self, max_age_seconds: float = 3600.0) -> None:
        now = time.time()
        expired = []
        for sid, dq in self._store.items():
            recent_ts = max((t.timestamp for t in dq), default=0)
            if now - recent_ts > max_age_seconds:
                expired.append(sid)
        for sid in expired:
            del self._store[sid]


short_term_memory = ShortTermMemory(max_rounds=MAX_ROUNDS)
