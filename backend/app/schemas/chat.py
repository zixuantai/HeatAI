from pydantic import BaseModel, Field


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolCallFunction


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=5000, description="用户消息")
    session_id: str | None = Field(None, description="会话ID，不传则自动创建新会话")
    quick_mode: bool = Field(False, description="快速模式，跳过知识库检索直接回复")
    voice: str = Field("longanhuan", description="TTS音色名称")
    images: list[str] = Field(default_factory=list, description="图片base64列表，用于视觉模型")


class ChatResponse(BaseModel):
    answer: str
    model: str
    session_id: str
    tool_calls: list[ToolCall] = []
