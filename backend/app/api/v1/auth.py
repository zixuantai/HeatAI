from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_refresh_token, CurrentUser
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshResponse, UserInfo
from app.services.auth_service import auth_service
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if req.password != req.password_confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="两次输入的密码不一致")

    import re
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$', req.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名支持字母、数字、下划线和中文，3-20位")

    try:
        await auth_service.register(db, req.username, req.password)
        return {"code": 0, "message": "注册成功", "data": None}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(
    req: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        ip = request.client.host if request.client else None
        result = await auth_service.login(db, req.username, req.password, ip)
        return {"code": 0, "message": "登录成功", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh")
async def refresh_token(
    refresh_token_str: Annotated[str, Depends(get_refresh_token)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        result = await auth_service.refresh(db, refresh_token_str)
        return {"code": 0, "message": "令牌刷新成功", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def logout(
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    refresh_header = request.headers.get("X-Refresh-Token", "")
    try:
        await auth_service.logout(db, token, refresh_header or None)
        return {"code": 0, "message": "退出成功", "data": None}
    except Exception:
        return {"code": 0, "message": "退出成功", "data": None}


@router.get("/me")
async def get_me(current_user: CurrentUser):
    user = current_user
    return {
        "code": 0,
        "message": "success",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "nickname": user.nickname,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else ""
        }
    }
