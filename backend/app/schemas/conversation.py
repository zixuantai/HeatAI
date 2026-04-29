from datetime import datetime
from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionDetailOut(SessionOut):
    messages: list[MessageOut] = []

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class SessionUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)


class PreferencesOut(BaseModel):
    profile: str = ""
    device_info: str = ""
    key_problems: str = ""
    interaction_summary: str = ""
    memory_summary: str = ""
