from pydantic import BaseModel, Field
from datetime import datetime


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="组织名称")
    description: str | None = Field(None, max_length=500, description="组织描述")
    avatar: str | None = Field(None, description="组织头像（Base64编码）")
    phone: str | None = Field(None, max_length=20, description="联系电话")
    email: str | None = Field(None, max_length=100, description="联系邮箱")


class OrganizationOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    avatar: str | None = None
    phone: str | None = None
    email: str | None = None
    invite_code: str
    created_by: str
    created_at: str
    member_count: int = 0

    class Config:
        from_attributes = True


class InviteCodeCreate(BaseModel):
    max_uses: int | None = Field(None, ge=1, description="最大使用次数，null表示无限")
    expires_at: datetime | None = Field(None, description="过期时间，null表示永不过期")


class InviteCodeOut(BaseModel):
    id: str
    code: str
    max_uses: int | None = None
    use_count: int
    expires_at: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class OrganizationMemberOut(BaseModel):
    user_id: str
    username: str
    nickname: str | None = None
    role: str
    joined_at: str

    class Config:
        from_attributes = True


class JoinByInviteCode(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="邀请码")


class UpdateMemberRole(BaseModel):
    role: str = Field(..., pattern="^admin$", description="角色：admin")
