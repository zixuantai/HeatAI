"""
知识库列表查询与排序服务
负责按不同维度（精选推荐、最热、最新、我的、我加入的）查询知识库列表
"""
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.knowledge_base import (
    KnowledgeBase, KnowledgeBaseFavorite, KnowledgeBaseMember
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
#  子查询工具
# ---------------------------------------------------------------

def _favorite_count():
    """当前知识库的收藏数子查询"""
    return (
        select(func.count(KnowledgeBaseFavorite.id))
        .where(KnowledgeBaseFavorite.knowledge_base_id == KnowledgeBase.id)
        .correlate(KnowledgeBase)
        .scalar_subquery()
    )


def _member_count():
    """当前知识库的成员数子查询"""
    return (
        select(func.count(KnowledgeBaseMember.id))
        .where(KnowledgeBaseMember.knowledge_base_id == KnowledgeBase.id)
        .correlate(KnowledgeBase)
        .scalar_subquery()
    )


# ---------------------------------------------------------------
#  排序策略 — 每种排序返回对应的 order_by 表达式
# ---------------------------------------------------------------

def _sort_popular():
    """最热：按点赞数 + 收藏数总和降序"""
    return (KnowledgeBase.like_count + _favorite_count()).desc()


def _sort_latest():
    """最新：按创建时间降序"""
    return KnowledgeBase.created_at.desc()


def _sort_recommended():
    """
    精选推荐 — Hot Score 算法
    Score = (点赞×3 + 收藏×2 + 成员×2 + 浏览×0.5) / (发布小时数 + 2)^1.5
    多维度人气信号加权，再经时间衰减，兼顾热门度与新鲜度
    """
    age_seconds = func.extract('epoch', func.now() - KnowledgeBase.created_at)
    age_hours = age_seconds / 3600.0
    time_decay = func.power(age_hours + 2, 1.5)
    popularity = (
        KnowledgeBase.like_count * 3 +
        _favorite_count() * 2 +
        _member_count() * 2 +
        KnowledgeBase.view_count * 0.5
    )
    return (popularity / time_decay).desc()


_SORT_STRATEGIES = {
    "popular":     _sort_popular,
    "latest":      _sort_latest,
    "recommended": _sort_recommended,
    "joined":      _sort_latest,       # 我加入的：按创建时间
    "mine":        _sort_latest,       # 我的：按创建时间
}


# ---------------------------------------------------------------
#  查询条件
# ---------------------------------------------------------------

def _build_conditions(user_id: str | None, search: str | None, sort_by: str):
    """构建 WHERE 条件列表"""
    conditions = [KnowledgeBase.status == "active"]

    if search:
        conditions.append(KnowledgeBase.name.ilike(f"%{search}%"))

    if sort_by == "mine" and user_id:
        conditions.append(KnowledgeBase.owner_id == user_id)

    if sort_by == "joined" and user_id:
        member_query = (
            select(KnowledgeBaseMember.knowledge_base_id)
            .where(KnowledgeBaseMember.user_id == user_id)
        )
        conditions.append(KnowledgeBase.id.in_(member_query))

    return conditions


# ---------------------------------------------------------------
#  公开接口
# ---------------------------------------------------------------

async def list_bases(
    db: AsyncSession,
    user_id: str | None = None,
    search: str | None = None,
    sort_by: str = "latest",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[KnowledgeBase], int]:
    """广场知识库列表查询"""

    conditions = _build_conditions(user_id, search, sort_by)

    # 总数
    count_result = await db.execute(
        select(func.count(KnowledgeBase.id)).where(*conditions)
    )
    total = count_result.scalar() or 0

    # 查询
    query = select(KnowledgeBase).where(*conditions)

    order_fn = _SORT_STRATEGIES.get(sort_by, _sort_latest)
    query = query.order_by(order_fn())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    bases = list(result.scalars().all())

    return bases, total