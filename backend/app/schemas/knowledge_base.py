from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="知识库名称")
    description: str | None = Field(None, max_length=500, description="知识库简介")
    avatar: str | None = Field(None, description="知识库头像(base64或URL)")
    cover_color: str | None = Field(None, description="封面渐变色")
    quick_questions: list[str] = Field(default_factory=list, description="快捷问题列表，最多4个")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    avatar: str | None = None
    cover_color: str | None = None
    quick_questions: list[str] | None = None
    is_recommended: bool | None = None


class QuickQuestionsPreviewIn(BaseModel):
    name: str = Field(..., description="知识库名称")
    description: str | None = Field(None, description="知识库简介")


class KnowledgeBaseOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    avatar: str | None = None
    cover_color: str | None = None
    owner_id: str
    owner_name: str | None = None
    owner_avatar: str | None = None
    status: str = "active"
    doc_count: int = 0
    view_count: int = 0
    like_count: int = 0
    is_recommended: bool = False
    is_liked: bool = False
    is_favorited: bool = False
    is_joined: bool = False
    member_count: int = 0
    quick_questions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    total: int
    items: list[KnowledgeBaseOut]


class QuickQuestionsUpdate(BaseModel):
    quick_questions: list[str] = Field(default_factory=list, max_length=4)


class KBChatRequest(BaseModel):
    message: str = Field(default="", max_length=5000, description="用户消息")
    session_id: str | None = Field(None, description="会话ID，不传则自动创建新会话")
    quick_mode: bool = Field(False, description="快速模式")
    voice: str = Field("longanhuan", description="TTS音色名称")
    images: list[str] = Field(default_factory=list, description="图片base64列表")
    personalization: dict[str, int] = Field(default_factory=dict, description="个性化参数")