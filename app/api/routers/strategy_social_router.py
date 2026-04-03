from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.stock_model import Strategy, User
from app.models.strategy_social_models import StrategyRating, StrategyFavorite, StrategyComment
from app.schemas.strategy_social_schema import (
    StrategyRatingCreate,
    StrategyRatingResponse,
    StrategyFavoriteResponse,
    StrategyCommentCreate,
    StrategyCommentResponse,
    StrategySocialSummary,
)
from app.services.strategy_social_service import StrategySocialService
from app.core.dependencies import get_current_user, get_current_user_optional
from app.models.stock_model import User

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies-social"])


# Dependency
async def get_strategy_social_service() -> StrategySocialService:
    async with async_session_factory() as session:
        yield StrategySocialService(session)


# --- 公共策略库 ---

@router.get("/public")
async def list_public_strategies(
    strategy_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    sort_by: str = "rating",
    limit: int = 20,
    offset: int = 0,
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """公共策略库列表（支持筛选/排序）"""
    filters = {}
    if strategy_type:
        filters["strategy_type"] = strategy_type
    if risk_level:
        filters["risk_level"] = risk_level

    strategies = await service.list_public_strategies(filters=filters or None, sort_by=sort_by, limit=limit, offset=offset)
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "strategy_type": getattr(s, "strategy_type", None),
                "rating": s.rating,
                "rating_count": s.rating_count,
                "favorite_count": s.favorite_count,
                "comment_count": s.comment_count,
                "backtest_count": s.backtest_count,
                "is_public": s.is_public,
                "is_official": s.is_official,
                "tags": s.tags,
            }
            for s in strategies
        ],
        "total": len(strategies),  # 简化实现，实际需 count 查询
    }


@router.get("/{strategy_id}/details", response_model=dict)
async def get_strategy_details(
    strategy_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """策略详情（含社交数据）"""
    summary = await service.get_strategy_social_summary(
        strategy_id=strategy_id,
        current_user_id=current_user.id if current_user else None,
    )
    return summary.model_dump()


# --- 评分 ---

@router.post("/{strategy_id}/rate", response_model=StrategyRatingResponse)
async def rate_strategy(
    strategy_id: int,
    data: StrategyRatingCreate,
    current_user: User = Depends(get_current_user),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """给策略评分（1-5 星）"""
    # 验证策略是否存在
    strategy = await service.db.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    rating_obj, new_avg = await service.rate_strategy(strategy_id, current_user.id, data)
    return rating_obj


@router.get("/my-ratings")
async def get_my_ratings(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """我的评分列表"""
    # 简化：直接查询 rating 表返回
    result = await service.db.execute(
        select(StrategyRating)
        .where(StrategyRating.user_id == current_user.id)
        .order_by(StrategyRating.created_at.desc())
        .limit(limit)
    )
    ratings = result.scalars().all()
    return [StrategyRatingResponse.model_validate(r) for r in ratings]


# --- 收藏 ---

@router.post("/{strategy_id}/favorite", response_model=dict)
async def toggle_favorite(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """收藏/取消收藏策略"""
    favorited = await service.toggle_favorite(strategy_id, current_user.id)
    return {
        "favorited": favorited,
        "favorite_count": (await service.db.execute(
            select(Strategy.favorite_count).where(Strategy.id == strategy_id)
        )).scalar_one(),
    }


@router.get("/my-favorites")
async def get_my_favorites(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """我的收藏列表"""
    favorites = await service.get_user_favorites(current_user.id, limit=limit)
    return [StrategyFavoriteResponse.model_validate(f) for f in favorites]


# --- 评论 ---

@router.get("/{strategy_id}/comments", response_model=list[StrategyCommentResponse])
async def get_comments(
    strategy_id: int,
    limit: int = 50,
    offset: int = 0,
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """获取策略评论列表（支持回复层级）"""
    comments = await service.get_comments(strategy_id, limit=limit, offset=offset)
    return comments


@router.post("/{strategy_id}/comments", response_model=StrategyCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    strategy_id: int,
    data: StrategyCommentCreate,
    current_user: User = Depends(get_current_user),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """发表评论（可回复）"""
    comment = await service.add_comment(
        strategy_id=strategy_id,
        user_id=current_user.id,
        content=data.content,
        parent_id=data.parent_id,
    )
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    service: StrategySocialService = Depends(get_strategy_social_service),
):
    """删除评论（仅作者）"""
    ok = await service.delete_comment(comment_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="评论不存在或无权删除")
