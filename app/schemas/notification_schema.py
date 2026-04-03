from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """通知响应"""
    id: int
    user_id: int
    type: str
    title: str
    message: str
    payload: Optional[dict] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationMarkRead(BaseModel):
    """标记已读"""
    is_read: bool = True
