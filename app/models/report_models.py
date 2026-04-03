from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.stock_model import Base


class UserReport(Base):
    """用户报告记录"""
    __tablename__ = "user_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="daily/weekly/monthly/custom")
    report_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True, comment="报告所属日期")
    html_content: Mapped[str] = mapped_column(Text, nullable=False, comment="HTML 报告正文")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="发送时间")
    sent_via: Mapped[list[str]] = mapped_column(JSONB, default=list, comment="推送渠道: in_app/email")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_user_reports_user_date', 'user_id', 'report_date'),
    )


class ReportPreference(Base):
    """用户报告偏好设置"""
    __tablename__ = "report_preferences"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="用户 ID")
    daily_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="启用每日报告")
    weekly_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="启用每周报告")
    monthly_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="启用月度报告")
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, comment="邮件推送")
    preferred_time: Mapped[datetime] = mapped_column(DateTime, default=datetime(2026, 1, 1, 8, 30), comment="偏好发送时间")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai", comment="时区")

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
