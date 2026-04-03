from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReportPreferenceBase(BaseModel):
    """报告偏好基础 Schema"""
    daily_enabled: bool = Field(default=True, description="启用每日报告")
    weekly_enabled: bool = Field(default=True, description="启用每周报告")
    monthly_enabled: bool = Field(default=True, description="启用月度报告")
    email_enabled: bool = Field(default=False, description="邮件推送")
    preferred_time: Optional[datetime] = Field(None, description="偏好发送时间")
    timezone: str = Field(default="Asia/Shanghai", description="时区")


class ReportPreferenceCreate(ReportPreferenceBase):
    """创建偏好（仅首次）"""
    pass


class ReportPreferenceUpdate(BaseModel):
    """更新偏好（部分字段可选）"""
    daily_enabled: Optional[bool] = None
    weekly_enabled: Optional[bool] = None
    monthly_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    preferred_time: Optional[datetime] = None
    timezone: Optional[str] = None


class ReportPreferenceResponse(ReportPreferenceBase):
    """偏好响应"""
    user_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class UserReportBase(BaseModel):
    """报告基础"""
    report_type: str
    report_date: datetime


class UserReportResponse(UserReportBase):
    """报告响应"""
    id: int
    user_id: int
    html_content: str
    sent_at: Optional[datetime] = None
    sent_via: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ReportGenerateRequest(BaseModel):
    """手动生成报告请求"""
    report_type: str = Field(..., description="报告类型: daily/weekly/monthly/custom")
    date: Optional[datetime] = Field(None, description="报告日期（不填则使用当前日期）")
    send_email: bool = Field(default=False, description="是否邮件发送")
