from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class StrategyRatingBase(BaseModel):
    """评分基础 Schema"""
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = Field(None, max_length=500, description="评分备注")


class StrategyRatingCreate(StrategyRatingBase):
    """创建评分"""
    pass


class StrategyRatingResponse(StrategyRatingBase):
    """评分响应"""
    id: int
    strategy_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyFavoriteResponse(BaseModel):
    """收藏响应"""
    id: int
    strategy_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyCommentBase(BaseModel):
    """评论基础 Schema"""
    content: str = Field(..., min_length=1, max_length=1000, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论 ID（用于回复）")


class StrategyCommentCreate(StrategyCommentBase):
    """创建评论"""
    pass


class StrategyCommentResponse(StrategyCommentBase):
    """评论响应"""
    id: int
    strategy_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategySocialSummary(BaseModel):
    """策略社交概览"""
    rating: float = Field(..., description="平均评分 0-5")
    rating_count: int = Field(..., description="评分人数")
    favorite_count: int = Field(..., description="收藏数")
    comment_count: int = Field(..., description="评论数")
    backtest_count: int = Field(..., description="被回测次数")
    view_count: int = Field(..., description="查看次数")
    user_rating: Optional[int] = Field(None, description="当前用户的评分（已登录时）")
    user_favorited: bool = Field(False, description="当前用户是否收藏")

    model_config = ConfigDict(from_attributes=True)
