from typing import Annotated
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decode_token
from app.services.auth_service import auth_service
from app.models.user import User
from app.models.organization import Organization, OrganizationMember

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")

    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证令牌无效或已过期")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型错误")

    if await auth_service.is_token_blacklisted(db, token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证令牌已失效")

    user_id = payload.get("sub")
    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_refresh_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)]
) -> str:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供刷新令牌")
    return credentials.credentials


class RequireRole:
    def __init__(self, *allowed_roles: str):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {', '.join(self.allowed_roles)}"
            )
        return current_user


AdminRequired = Annotated[User, Depends(RequireRole("admin"))]


async def get_current_organization(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_organization_id: str | None = Header(None, alias="X-Organization-Id")
) -> tuple[Organization | None, OrganizationMember | None]:
    if x_organization_id:
        result = await db.execute(
            select(Organization, OrganizationMember)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(
                Organization.id == x_organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不属于该组织"
            )
        return row[0], row[1]

    result = await db.execute(
        select(Organization, OrganizationMember)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
    )
    rows = result.all()

    if len(rows) == 1:
        return rows[0][0], rows[0][1]

    return None, None


CurrentOrganization = Annotated[
    tuple[Organization | None, OrganizationMember | None],
    Depends(get_current_organization)
]
