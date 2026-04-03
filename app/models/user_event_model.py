import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import Index, String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserEvent(Base):
    """用户行为事件表（分区 + 归档策略由 Alembic 迁移处理）"""

    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    page: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_user_events_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<UserEvent id={self.id} type={self.event_type} user={self.user_id}>"
