from typing import Optional
from datetime import datetime

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy_social_models import StrategyRating, StrategyFavorite, StrategyComment
from app.models.stock_model import Strategy
from app.schemas.strategy_social_schema import (
    StrategyRatingCreate,
    StrategyRatingResponse,
    StrategyFavoriteResponse,
    StrategyCommentCreate,
    StrategyCommentResponse,
    StrategySocialSummary,
)


class StrategySocialService:
    """策略社交功能服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- 评分 ---

    async def rate_strategy(
        self,
        strategy_id: int,
        user_id: int,
        data: StrategyRatingCreate
    ) -> tuple[StrategyRatingResponse, float]:
        """用户给策略评分（创建或更新）"""
        # 检查是否已评分
        existing = await self.db.execute(
            select(StrategyRating).where(
                StrategyRating.strategy_id == strategy_id,
                StrategyRating.user_id == user_id,
            )
        )
        old_rating = existing.scalar_one_or_none()

        if old_rating:
            # 更新评分
            old_score = float(old_rating.rating)
            old_rating.rating = data.rating
            old_rating.comment = data.comment
            old_rating.updated_at = datetime.utcnow()
            rating_obj = old_rating
        else:
            # 新建评分
            rating_obj = StrategyRating(
                strategy_id=strategy_id,
                user_id=user_id,
                rating=data.rating,
                comment=data.comment,
            )
            self.db.add(rating_obj)
            await self.db.flush()

        # 重新计算平均分
        await self._recalculate_strategy_rating(strategy_id)

        await self.db.refresh(rating_obj)
        return StrategyRatingResponse.model_validate(rating_obj), float(rating_obj.rating)

    async def _recalculate_strategy_rating(self, strategy_id: int):
        """重新计算策略的平均评分和评分人数"""
        result = await self.db.execute(
            select(
                func.avg(StrategyRating.rating).label("avg_rating"),
                func.count(StrategyRating.id).label("count"),
            ).where(StrategyRating.strategy_id == strategy_id)
        )
        row = result.first()
        avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
        count = row.count or 0

        await self.db.execute(
            update(Strategy)
            .where(Strategy.id == strategy_id)
            .values(rating=round(avg_rating, 2), rating_count=count)
        )

    async def get_user_rating(self, strategy_id: int, user_id: int) -> Optional[int]:
        """获取用户对该策略的评分"""
        result = await self.db.execute(
            select(StrategyRating.rating).where(
                StrategyRating.strategy_id == strategy_id,
                StrategyRating.user_id == user_id,
            )
        )
        row = result.first()
        return row[0] if row else None

    # --- 收藏 ---

    async def toggle_favorite(self, strategy_id: int, user_id: int) -> bool:
        """切换收藏状态，返回 True 表示已收藏"""
        # 检查是否已收藏
        result = await self.db.execute(
            select(StrategyFavorite).where(
                StrategyFavorite.strategy_id == strategy_id,
                StrategyFavorite.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 取消收藏
            await self.db.delete(existing)
            await self.db.execute(
                update(Strategy)
                .where(Strategy.id == strategy_id)
                .values(favorite_count=Strategy.favorite_count - 1)
            )
            await self.db.flush()
            return False
        else:
            # 添加收藏
            fav = StrategyFavorite(strategy_id=strategy_id, user_id=user_id)
            self.db.add(fav)
            await self.db.execute(
                update(Strategy)
                .where(Strategy.id == strategy_id)
                .values(favorite_count=Strategy.favorite_count + 1)
            )
            await self.db.flush()
            return True

    async def is_favorited(self, strategy_id: int, user_id: int) -> bool:
        """查询是否已收藏"""
        result = await self.db.execute(
            select(StrategyFavorite).where(
                StrategyFavorite.strategy_id == strategy_id,
                StrategyFavorite.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_user_favorites(self, user_id: int, limit: int = 20) -> list[StrategyFavoriteResponse]:
        """获取用户收藏的策略列表"""
        result = await self.db.execute(
            select(StrategyFavorite)
            .where(StrategyFavorite.user_id == user_id)
            .order_by(StrategyFavorite.created_at.desc())
            .limit(limit)
        )
        return [StrategyFavoriteResponse.model_validate(f) for f in result.scalars().all()]

    # --- 评论 ---

    async def add_comment(
        self,
        strategy_id: int,
        user_id: int,
        content: str,
        parent_id: Optional[int] = None,
    ) -> StrategyCommentResponse:
        """发表评论（支持回复）"""
        comment = StrategyComment(
            strategy_id=strategy_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
        )
        self.db.add(comment)
        await self.db.flush()

        # 更新评论计数
        await self.db.execute(
            update(Strategy)
            .where(Strategy.id == strategy_id)
            .values(comment_count=Strategy.comment_count + 1)
        )
        await self.db.flush()
        await self.db.refresh(comment)
        return StrategyCommentResponse.model_validate(comment)

    async def get_comments(
        self,
        strategy_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StrategyCommentResponse]:
        """获取策略评论列表（按时间正序，支持层级）"""
        result = await self.db.execute(
            select(StrategyComment)
            .where(StrategyComment.strategy_id == strategy_id, StrategyComment.parent_id.is_(None))
            .order_by(StrategyComment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        comments = result.scalars().all()

        # 加载回复（简单实现：一次性加载所有评论）
        all_result = await self.db.execute(
            select(StrategyComment)
            .where(StrategyComment.strategy_id == strategy_id)
            .order_by(StrategyComment.created_at.asc())
        )
        all_comments = all_result.scalars().all()

        # 构建父子关系（前端递归渲染）
        comment_map = {c.id: StrategyCommentResponse.model_validate(c) for c in all_comments}
        for c in comment_map.values():
            c.__dict__.setdefault("replies", [])

        root_comments = []
        for c in all_comments:
            resp = comment_map[c.id]
            if c.parent_id:
                parent = comment_map.get(c.parent_id)
                if parent:
                    parent.__dict__.setdefault("replies", []).append(resp)
            else:
                root_comments.append(resp)

        return root_comments[:limit]

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        """删除评论（仅作者或管理员）"""
        result = await self.db.execute(
            select(StrategyComment).where(
                StrategyComment.id == comment_id,
                StrategyComment.user_id == user_id,
            )
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return False

        strategy_id = comment.strategy_id
        await self.db.delete(comment)
        await self.db.execute(
            update(Strategy)
            .where(Strategy.id == strategy_id)
            .values(comment_count=Strategy.comment_count - 1)
        )
        await self.db.flush()
        return True

    # --- 策略详情与社会概览 ---

    async def get_strategy_social_summary(
        self,
        strategy_id: int,
        current_user_id: Optional[int] = None,
    ) -> StrategySocialSummary:
        """获取策略社交概览（评分/收藏/评论统计 + 用户状态）"""
        strategy = await self.db.get(Strategy, strategy_id)
        if not strategy:
            raise ValueError("Strategy not found")

        user_rating = None
        user_favorited = False
        if current_user_id:
            user_rating = await self.get_user_rating(strategy_id, current_user_id)
            user_favorited = await self.is_favorited(strategy_id, current_user_id)

        return StrategySocialSummary(
            rating=strategy.rating,
            rating_count=strategy.rating_count,
            favorite_count=strategy.favorite_count,
            comment_count=strategy.comment_count,
            backtest_count=strategy.backtest_count,
            view_count=strategy.view_count,
            user_rating=user_rating,
            user_favorited=user_favorited,
        )

    # --- 公共策略列表 ---

    async def list_public_strategies(
        self,
        filters: Optional[dict] = None,
        sort_by: str = "rating",
        limit: int = 20,
        offset: int = 0,
    ) -> list[Strategy]:
        """列出公开策略"""
        stmt = select(Strategy).where(Strategy.is_public == True)

        if filters:
            if "strategy_type" in filters:
                stmt = stmt.where(Strategy.strategy_type == filters["strategy_type"])
            if "risk_level" in filters:
                stmt = stmt.where(Strategy.risk_level == filters["risk_level"])
            if "tags" in filters:
                for tag in filters["tags"]:
                    stmt = stmt.where(Strategy.tags.contains([tag]))

        # 排序
        sort_column = getattr(Strategy, sort_by, Strategy.rating)
        stmt = stmt.order_by(sort_column.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
