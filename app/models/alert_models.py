from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.stock_model import Base


class AlertCondition(Base):
    """预警条件定义模型"""
    __tablename__ = "alert_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="预警名称")
    code: Mapped[str] = mapped_column(String(20), nullable=False, comment="股票代码", index=True)

    # 预警类型: price/change/rsi/pattern/fund
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 条件表达式：{type, operator, value, pattern_name?}
    # 示例：{"type": "price", "operator": "gt", "value": 30.0}
    # 示例：{"type": "rsi", "operator": "lt", "value": 30}
    # 示例：{"type": "pattern", "pattern_name": "hammer"}
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # 推送渠道：in_app / email
    notify_channels: Mapped[list[str]] = mapped_column(JSONB, default=lambda: ["in_app"])

    # 冷却机制：同条件 last_triggered_at 后 1 小时内不再推送
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_alert_conditions_user_active', 'user_id', 'is_active'),
        Index('ix_alert_conditions_type_active', 'condition_type', 'is_active'),
    )


class Notification(Base):
    """应用内通知模型（如不存在则新建，如存在则复用）"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, comment="alert/backtest_done/pattern_detected/report_available")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # 关联数据（如预警ID、股票代码）
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_notifications_user_unread', 'user_id', 'is_read'),
    )
