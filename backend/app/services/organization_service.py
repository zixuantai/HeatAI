import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization, OrganizationMember, InviteCode, generate_invite_code
from app.models.user import User

logger = logging.getLogger(__name__)


class OrganizationService:

    @staticmethod
    async def create_organization(
        db: AsyncSession,
        user_id: str,
        name: str,
        description: str | None = None,
        avatar: str | None = None,
        phone: str | None = None,
        email: str | None = None
    ) -> tuple[Organization, InviteCode]:
        existing_org = await db.execute(
            select(Organization).where(Organization.created_by == user_id)
        )
        if existing_org.scalar_one_or_none():
            raise ValueError("您已经创建过组织，一个管理员只能创建一个组织")

        org = Organization(
            name=name,
            description=description,
            avatar=avatar,
            phone=phone,
            email=email,
            created_by=user_id,
            invite_code=generate_invite_code()
        )
        db.add(org)
        await db.flush()

        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role="owner"
        )
        db.add(member)

        invite_code = InviteCode(
            organization_id=org.id,
            code=generate_invite_code(),
            created_by=user_id
        )
        db.add(invite_code)

        await db.commit()
        await db.refresh(org)
        await db.refresh(invite_code)

        logger.info(f"组织创建成功: {org.name} (ID: {org.id}), 创建者: {user_id}")
        return org, invite_code

    @staticmethod
    async def join_by_invite_code(
        db: AsyncSession,
        user_id: str,
        code: str
    ) -> tuple[Organization, OrganizationMember]:
        result = await db.execute(
            select(InviteCode).where(InviteCode.code == code, InviteCode.is_active == True)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            raise ValueError("邀请码无效或已停用")

        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("邀请码已过期")

        if invite.max_uses is not None and invite.use_count >= invite.max_uses:
            raise ValueError("邀请码已达到最大使用次数")

        existing_member = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == invite.organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        if existing_member.scalar_one_or_none():
            raise ValueError("您已经是该组织的成员")

        org_result = await db.execute(
            select(Organization).where(Organization.id == invite.organization_id)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise ValueError("组织不存在")

        member = OrganizationMember(
            organization_id=invite.organization_id,
            user_id=user_id,
            role="admin"
        )
        db.add(member)

        invite.use_count += 1
        await db.commit()
        await db.refresh(org)
        await db.refresh(member)

        logger.info(f"用户 {user_id} 通过邀请码加入组织 {org.name} (ID: {org.id})")
        return org, member

    @staticmethod
    async def create_invite_code(
        db: AsyncSession,
        org_id: str,
        user_id: str,
        max_uses: int | None = None,
        expires_at: datetime | None = None
    ) -> InviteCode:
        invite_code = InviteCode(
            organization_id=org_id,
            code=generate_invite_code(),
            created_by=user_id,
            max_uses=max_uses,
            expires_at=expires_at
        )
        db.add(invite_code)
        await db.commit()
        await db.refresh(invite_code)

        logger.info(f"邀请码创建成功: {invite_code.code}, 组织ID: {org_id}")
        return invite_code

    @staticmethod
    async def list_invite_codes(db: AsyncSession, org_id: str) -> list[InviteCode]:
        result = await db.execute(
            select(InviteCode)
            .where(InviteCode.organization_id == org_id)
            .order_by(InviteCode.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def deactivate_invite_code(db: AsyncSession, code_id: str) -> InviteCode | None:
        result = await db.execute(
            select(InviteCode).where(InviteCode.id == code_id)
        )
        invite = result.scalar_one_or_none()

        if not invite:
            return None

        invite.is_active = False
        await db.commit()
        await db.refresh(invite)

        logger.info(f"邀请码已停用: {invite.code} (ID: {code_id})")
        return invite

    @staticmethod
    async def list_members(db: AsyncSession, org_id: str) -> list[dict]:
        result = await db.execute(
            select(OrganizationMember, User)
            .join(User, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.organization_id == org_id)
            .order_by(OrganizationMember.joined_at.desc())
        )
        rows = result.all()
        return [
            {
                "user_id": row[0].user_id,
                "username": row[1].username,
                "nickname": row[1].nickname,
                "role": row[0].role,
                "joined_at": row[0].joined_at.isoformat() if row[0].joined_at else None
            }
            for row in rows
        ]

    @staticmethod
    async def update_member_role(
        db: AsyncSession,
        org_id: str,
        operator_id: str,
        target_user_id: str,
        new_role: str
    ) -> OrganizationMember | None:
        operator_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == operator_id
            )
        )
        operator = operator_result.scalar_one_or_none()

        if not operator or operator.role not in ("owner", "admin"):
            raise ValueError("权限不足，只有 owner 或 admin 可以修改成员角色")

        target_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == target_user_id
            )
        )
        target = target_result.scalar_one_or_none()

        if not target:
            return None

        if target.role == "owner":
            raise ValueError("不能修改 owner 的角色")

        if operator.role == "admin" and target.role == "admin":
            raise ValueError("admin 不能修改其他 admin 的角色")

        target.role = new_role
        await db.commit()
        await db.refresh(target)

        logger.info(f"成员角色更新: 用户 {target_user_id} 在组织 {org_id} 的角色改为 {new_role}")
        return target

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        org_id: str,
        operator_id: str,
        target_user_id: str
    ) -> bool:
        operator_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == operator_id
            )
        )
        operator = operator_result.scalar_one_or_none()

        if not operator or operator.role not in ("owner", "admin"):
            raise ValueError("权限不足，只有 owner 或 admin 可以移除成员")

        target_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == target_user_id
            )
        )
        target = target_result.scalar_one_or_none()

        if not target:
            return False

        if target.role == "owner":
            raise ValueError("不能移除 owner")

        if operator.role == "admin" and target.role == "admin":
            raise ValueError("admin 不能移除其他 admin")

        await db.delete(target)
        await db.commit()

        logger.info(f"成员已移除: 用户 {target_user_id} 从组织 {org_id}")
        return True


organization_service = OrganizationService()
