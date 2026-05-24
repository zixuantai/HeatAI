import uuid
import json
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_color: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    owner_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    quick_questions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def quick_questions(self) -> list[str]:
        if not self.quick_questions_json:
            return []
        try:
            return json.loads(self.quick_questions_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @quick_questions.setter
    def quick_questions(self, value: list[str]):
        self.quick_questions_json = json.dumps(value, ensure_ascii=False)


class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "document_id", name="uq_kb_doc"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KnowledgeBaseLike(Base):
    __tablename__ = "knowledge_base_likes"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "user_id", name="uq_kb_like"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KnowledgeBaseFavorite(Base):
    __tablename__ = "knowledge_base_favorites"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "user_id", name="uq_kb_favorite"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KnowledgeBaseMember(Base):
    __tablename__ = "knowledge_base_members"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "user_id", name="uq_kb_member"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())