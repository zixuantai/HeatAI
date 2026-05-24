from datetime import datetime, timezone, timedelta
import os
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserSession, TokenBlacklist
from app.models.organization import Organization, OrganizationMember, InviteCode
from app.models.conversation import ConversationSession, Message
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase, KnowledgeBaseLike, KnowledgeBaseFavorite, KnowledgeBaseMember, KnowledgeBaseDocument
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.services.retrieval.milvus_service import milvus_service
from app.services.retrieval.bm25_service import bm25_service
import logging

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    async def register(db: AsyncSession, username: str, password: str, role: str = "user") -> User:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise ValueError("用户名已存在")

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role if role in ("user", "admin") else "user"
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
    async def update_user_profile(db: AsyncSession, user: User, username: str | None, email: str | None, phone: str | None, nickname: str | None, avatar: str | None = None) -> User:
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

        if avatar is not None:
            user.avatar = avatar

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_organizations(db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(Organization, OrganizationMember)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user_id)
            .order_by(OrganizationMember.joined_at.desc())
        )
        rows = result.all()
        return [
            {
                "id": row[0].id,
                "name": row[0].name,
                "role": row[1].role,
                "joined_at": row[1].joined_at.isoformat() if row[1].joined_at else None
            }
            for row in rows
        ]

    @staticmethod
    async def delete_account(db: AsyncSession, user: User, password: str) -> None:
        if not verify_password(password, user.password_hash):
            raise ValueError("密码错误")

        user_id = user.id

        # ── 收集所有文档信息（用于后续清理 Milvus / BM25 / 文件）──
        # 用户直接上传的文档
        user_docs_result = await db.execute(
            select(Document.id, Document.filename, Document.organization_id)
            .where(Document.user_id == user_id)
        )
        user_docs = user_docs_result.all()  # [(id, filename, org_id), ...]

        # 知识库关联的文档
        kb_docs_result = await db.execute(
            select(KnowledgeBaseDocument.document_id)
            .where(KnowledgeBaseDocument.knowledge_base_id.in_(
                select(KnowledgeBase.id).where(KnowledgeBase.owner_id == user_id)
            ))
        )
        kb_doc_ids = kb_docs_result.scalars().all()

        # ── 删除用户会话 ──
        await db.execute(delete(UserSession).where(UserSession.user_id == user_id))

        # ── 删除用户创建的组织（级联删除其成员和邀请码）──
        org_ids = (await db.execute(select(Organization.id).where(Organization.created_by == user_id))).scalars().all()
        if org_ids:
            await db.execute(delete(InviteCode).where(InviteCode.organization_id.in_(org_ids)))
            await db.execute(delete(OrganizationMember).where(OrganizationMember.organization_id.in_(org_ids)))
        await db.execute(delete(Organization).where(Organization.created_by == user_id))

        # ── 删除组织成员关系（用户加入的其他组织）──
        await db.execute(delete(OrganizationMember).where(OrganizationMember.user_id == user_id))

        # ── 删除用户创建的邀请码 ──
        await db.execute(delete(InviteCode).where(InviteCode.created_by == user_id))

        # ── 删除对话和消息 ──
        session_ids = (await db.execute(select(ConversationSession.id).where(ConversationSession.user_id == user_id))).scalars().all()
        if session_ids:
            await db.execute(delete(Message).where(Message.session_id.in_(session_ids)))
        await db.execute(delete(ConversationSession).where(ConversationSession.user_id == user_id))

        # ── 删除知识库相关数据 ──
        kb_ids = (await db.execute(select(KnowledgeBase.id).where(KnowledgeBase.owner_id == user_id))).scalars().all()
        if kb_ids:
            await db.execute(delete(KnowledgeBaseDocument).where(KnowledgeBaseDocument.knowledge_base_id.in_(kb_ids)))
            await db.execute(delete(KnowledgeBaseLike).where(KnowledgeBaseLike.knowledge_base_id.in_(kb_ids)))
            await db.execute(delete(KnowledgeBaseFavorite).where(KnowledgeBaseFavorite.knowledge_base_id.in_(kb_ids)))
            await db.execute(delete(KnowledgeBaseMember).where(KnowledgeBaseMember.knowledge_base_id.in_(kb_ids)))
        await db.execute(delete(KnowledgeBaseMember).where(KnowledgeBaseMember.user_id == user_id))
        await db.execute(delete(KnowledgeBaseLike).where(KnowledgeBaseLike.user_id == user_id))
        await db.execute(delete(KnowledgeBaseFavorite).where(KnowledgeBaseFavorite.user_id == user_id))
        await db.execute(delete(KnowledgeBase).where(KnowledgeBase.owner_id == user_id))

        # ── 删除用户文档（SQL）──
        await db.execute(delete(Document).where(Document.user_id == user_id))

        # ── 删除用户 ──
        await db.execute(delete(User).where(User.id == user_id))

        await db.commit()

        # ── 清理外部资源（Milvus / BM25 / 文件系统）──
        all_doc_ids = [doc[0] for doc in user_docs] + list(kb_doc_ids)
        for doc_id in set(all_doc_ids):
            try:
                milvus_service.delete_by_document_id(doc_id)
            except Exception as e:
                logger.warning(f"Milvus 删除失败 [doc={doc_id}]: {e}")

        for doc_id in set(kb_doc_ids):
            try:
                bm25_service.remove_by_document_id(doc_id)
            except Exception as e:
                logger.warning(f"BM25 删除失败 [doc={doc_id}]: {e}")

        for doc_id, filename, org_id in user_docs:
            try:
                bm25_service.remove_by_document_id(doc_id, org_id=org_id)
            except Exception as e:
                logger.warning(f"BM25 删除失败 [doc={doc_id}]: {e}")
            try:
                file_path = os.path.join(os.path.abspath(settings.UPLOAD_DIR), filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"文件删除失败 [doc={doc_id}]: {e}")

        logger.info(f"账号注销完成: user_id={user_id}, 清理文档数={len(user_docs)}")


auth_service = AuthService()
