from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    session_id: str | None = Field(None, description="会话ID，不传则自动创建新会话")


class ChatResponse(BaseModel):
    answer: str
    model: str
    session_id: str
