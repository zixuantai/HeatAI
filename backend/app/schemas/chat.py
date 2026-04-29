from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")


class ChatResponse(BaseModel):
    answer: str
    model: str
