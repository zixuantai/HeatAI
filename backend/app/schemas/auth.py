from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")
    password_confirm: str = Field(..., min_length=6, max_length=20, description="确认密码")


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
    role: str
    status: str
    created_at: str

    class Config:
        from_attributes = True
