from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertConditionBase(BaseModel):
    """预警条件基础 Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="预警名称")
    code: str = Field(..., min_length=1, max_length=20, description="股票代码")
    condition: dict = Field(..., description="条件表达式 JSON")
    is_active: bool = Field(default=True, description="是否启用")
    notify_channels: list[str] = Field(default=["in_app"], description="通知渠道")


class AlertConditionCreate(AlertConditionBase):
    """创建预警条件"""
    pass


class AlertConditionUpdate(BaseModel):
    """更新预警条件（部分字段可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    condition: Optional[dict] = None
    is_active: Optional[bool] = None
    notify_channels: Optional[list[str]] = None


class AlertConditionResponse(AlertConditionBase):
    """预警条件响应"""
    id: int
    user_id: int
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertConditionSimple(BaseModel):
    """简化版预警（列表展示）"""
    id: int
    name: str
    code: str
    condition_type: str
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
