import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOut,
    InviteCodeCreate,
    InviteCodeOut,
    OrganizationMemberOut,
    JoinByInviteCode,
    UpdateMemberRole,
)
from app.services.organization_service import organization_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["组织管理"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: OrganizationCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        org, invite_code = await organization_service.create_organization(
            db, current_user.id, req.name, req.description
        )
        return {
            "code": 0,
            "message": "组织创建成功",
            "data": {
                "organization": OrganizationOut(
                    id=org.id,
                    name=org.name,
                    description=org.description,
                    invite_code=org.invite_code,
                    created_by=org.created_by,
                    created_at=org.created_at.isoformat() if org.created_at else ""
                ).model_dump(mode="json"),
                "default_invite_code": InviteCodeOut(
                    id=invite_code.id,
                    code=invite_code.code,
                    max_uses=invite_code.max_uses,
                    use_count=invite_code.use_count,
                    expires_at=invite_code.expires_at.isoformat() if invite_code.expires_at else None,
                    is_active=invite_code.is_active
                ).model_dump(mode="json")
            }
        }
    except Exception as e:
        logger.exception(f"创建组织失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=dict)
async def list_my_organizations(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(Organization, OrganizationMember)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(OrganizationMember.joined_at.desc())
    )
    rows = result.all()
    organizations = [
        OrganizationOut(
            id=row[0].id,
            name=row[0].name,
            description=row[0].description,
            invite_code=row[0].invite_code,
            created_by=row[0].created_by,
            created_at=row[0].created_at.isoformat() if row[0].created_at else ""
        ).model_dump(mode="json")
        for row in rows
    ]
    return {"code": 0, "message": "success", "data": organizations}


@router.get("/{org_id}", response_model=dict)
async def get_organization(
    org_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您不属于该组织")

    org_result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")

    return {
        "code": 0,
        "message": "success",
        "data": OrganizationOut(
            id=org.id,
            name=org.name,
            description=org.description,
            invite_code=org.invite_code,
            created_by=org.created_by,
            created_at=org.created_at.isoformat() if org.created_at else ""
        ).model_dump(mode="json")
    }


@router.post("/join", response_model=dict)
async def join_by_invite_code(
    req: JoinByInviteCode,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        org, member = await organization_service.join_by_invite_code(db, current_user.id, req.code)
        return {
            "code": 0,
            "message": "加入组织成功",
            "data": {
                "organization_id": org.id,
                "organization_name": org.name,
                "role": member.role
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{org_id}/members", response_model=dict)
async def list_members(
    org_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您不属于该组织")

    members = await organization_service.list_members(db, org_id)
    return {"code": 0, "message": "success", "data": members}


@router.put("/{org_id}/members/{target_user_id}", response_model=dict)
async def update_member_role(
    org_id: str,
    target_user_id: str,
    req: UpdateMemberRole,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        member = await organization_service.update_member_role(
            db, org_id, current_user.id, target_user_id, req.role
        )
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")
        return {"code": 0, "message": "角色更新成功", "data": {"role": member.role}}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{org_id}/members/{target_user_id}", response_model=dict)
async def remove_member(
    org_id: str,
    target_user_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        success = await organization_service.remove_member(db, org_id, current_user.id, target_user_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")
        return {"code": 0, "message": "成员已移除", "data": None}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{org_id}/invite-codes", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_invite_code(
    org_id: str,
    req: InviteCodeCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，只有 owner 或 admin 可以创建邀请码")

    try:
        invite_code = await organization_service.create_invite_code(
            db, org_id, current_user.id, req.max_uses, req.expires_at
        )
        return {
            "code": 0,
            "message": "邀请码创建成功",
            "data": InviteCodeOut(
                id=invite_code.id,
                code=invite_code.code,
                max_uses=invite_code.max_uses,
                use_count=invite_code.use_count,
                expires_at=invite_code.expires_at.isoformat() if invite_code.expires_at else None,
                is_active=invite_code.is_active
            ).model_dump(mode="json")
        }
    except Exception as e:
        logger.exception(f"创建邀请码失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{org_id}/invite-codes", response_model=dict)
async def list_invite_codes(
    org_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，只有 owner 或 admin 可以查看邀请码")

    invite_codes = await organization_service.list_invite_codes(db, org_id)
    return {
        "code": 0,
        "message": "success",
        "data": [
            InviteCodeOut(
                id=ic.id,
                code=ic.code,
                max_uses=ic.max_uses,
                use_count=ic.use_count,
                expires_at=ic.expires_at.isoformat() if ic.expires_at else None,
                is_active=ic.is_active
            ).model_dump(mode="json")
            for ic in invite_codes
        ]
    }


@router.delete("/invite-codes/{code_id}", response_model=dict)
async def deactivate_invite_code(
    code_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    invite = await organization_service.deactivate_invite_code(db, code_id)
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邀请码不存在")

    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == invite.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member or member.role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    return {"code": 0, "message": "邀请码已停用", "data": None}
