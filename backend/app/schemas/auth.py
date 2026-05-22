from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")
    password_confirm: str = Field(..., min_length=6, max_length=20, description="确认密码")
    role: str = Field(default="user", description="角色: user 或 admin")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserInfo(BaseModel):
    id: str
    username: str
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    role: str
    status: str
    created_at: str
    organizations: list[dict] | None = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=20, description="用户名")
    email: str | None = Field(None, max_length=100, description="邮箱")
    phone: str | None = Field(None, max_length=20, description="手机号")
    nickname: str | None = Field(None, max_length=50, description="昵称")
    avatar: str | None = Field(None, description="头像(base64)")
