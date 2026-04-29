from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserSession, TokenBlacklist
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings


class AuthService:

    @staticmethod
    async def register(db: AsyncSession, username: str, password: str) -> User:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        user = User(
            username=username,
            password_hash=hash_password(password)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def login(db: AsyncSession, username: str, password: str, ip_address: str | None = None) -> dict:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")

        if user.status != "active":
            raise ValueError("账户已被禁用，请联系管理员")

        now = datetime.now(timezone.utc)
        user.last_login_at = now.replace(tzinfo=None)
        user.last_login_ip = ip_address

        access_token = create_access_token(user.id, user.username, user.role)
        refresh_token = create_refresh_token(user.id, user.username, user.role)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash=hash_password(refresh_token),
            ip_address=ip_address,
            expires_at=(now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).replace(tzinfo=None)
        )
        db.add(session)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    @staticmethod
    async def refresh(db: AsyncSession, refresh_token_str: str) -> dict:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("无效的刷新令牌")

        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("用户不存在")

        if user.status != "active":
            raise ValueError("账户已被禁用")

        access_token = create_access_token(user.id, user.username, user.role)
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    @staticmethod
    async def logout(db: AsyncSession, token: str, refresh_token_str: str | None = None) -> None:
        payload = decode_token(token)
        if payload:
            expires_at = datetime.fromtimestamp(payload.get("exp", 0), tz=None)
            blacklist = TokenBlacklist(
                token=token,
                token_type="access",
                expires_at=expires_at
            )
            db.add(blacklist)

        if refresh_token_str:
            payload_refresh = decode_token(refresh_token_str)
            if payload_refresh:
                expires_at = datetime.fromtimestamp(payload_refresh.get("exp", 0), tz=None)
                blacklist_refresh = TokenBlacklist(
                    token=refresh_token_str,
                    token_type="refresh",
                    expires_at=expires_at
                )
                db.add(blacklist_refresh)

        await db.commit()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def is_token_blacklisted(db: AsyncSession, token: str) -> bool:
        result = await db.execute(select(TokenBlacklist).where(TokenBlacklist.token == token))
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def update_user_profile(db: AsyncSession, user: User, username: str | None, email: str | None, phone: str | None, nickname: str | None) -> User:
        if username is not None and username != user.username:
            result = await db.execute(select(User).where(User.username == username))
            existing = result.scalar_one_or_none()
            if existing and existing.id != user.id:
                raise ValueError("用户名已被占用")

            import re
            if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$', username):
                raise ValueError("用户名支持字母、数字、下划线和中文，3-20位")

            user.username = username

        if email is not None and email != user.email:
            if email:
                result = await db.execute(select(User).where(User.email == email))
                existing = result.scalar_one_or_none()
                if existing and existing.id != user.id:
                    raise ValueError("邮箱已被占用")
            user.email = email

        if phone is not None and phone != user.phone:
            if phone:
                result = await db.execute(select(User).where(User.phone == phone))
                existing = result.scalar_one_or_none()
                if existing and existing.id != user.id:
                    raise ValueError("手机号已被占用")
            user.phone = phone

        if nickname is not None:
            user.nickname = nickname

        await db.commit()
        await db.refresh(user)
        return user


auth_service = AuthService()
