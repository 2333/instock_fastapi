from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.stock_model import Base


class StrategyRating(Base):
    """策略评分模型"""
    __tablename__ = "strategy_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="评分 1-5")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="评分备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('strategy_id', 'user_id', name='uq_strategy_user_rating'),
        Index('ix_strategy_ratings_strategy', 'strategy_id'),
        Index('ix_strategy_ratings_user', 'user_id'),
    )


class StrategyFavorite(Base):
    """策略收藏模型"""
    __tablename__ = "strategy_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('strategy_id', 'user_id', name='uq_strategy_user_favorite'),
        Index('ix_strategy_favorites_strategy', 'strategy_id'),
        Index('ix_strategy_favorites_user', 'user_id'),
    )


class StrategyComment(Base):
    """策略评论模型（支持回复）"""
    __tablename__ = "strategy_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("strategy_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_strategy_comments_strategy', 'strategy_id'),
        Index('ix_strategy_comments_user', 'user_id'),
        Index('ix_strategy_comments_parent', 'parent_id'),
    )
