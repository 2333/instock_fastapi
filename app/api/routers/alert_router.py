from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.alert_models import AlertCondition, Notification
from app.schemas.alert_schema import (
    AlertConditionCreate,
    AlertConditionResponse,
    AlertConditionSimple,
    AlertConditionUpdate,
)
from app.schemas.notification_schema import NotificationMarkRead, NotificationResponse
from app.services.alert_service import AlertService
from app.core.dependencies import get_current_user
from app.models.stock_model import User

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# Dependency
async def get_alert_service() -> AlertService:
    async with async_session_factory() as session:
        yield AlertService(session)


# --- Alert Conditions ---

@router.get("/conditions", response_model=list[AlertConditionSimple])
async def list_alerts(
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """列出我的预警条件"""
    alerts = await service.get_user_alerts(current_user.id, active_only=active_only)
    return [
        AlertConditionSimple(
            id=a.id,
            name=a.name,
            code=a.code,
            condition_type=a.condition.get("type", "unknown"),
            is_active=a.is_active,
            last_triggered_at=a.last_triggered_at,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.post("/conditions", response_model=AlertConditionResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertConditionCreate,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """创建预警条件"""
    alert = await service.create_alert(current_user.id, data)
    return AlertConditionResponse.model_validate(alert)


@router.get("/conditions/{alert_id}", response_model=AlertConditionResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """查询单个预警条件"""
    alert = await service.get_alert(alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    return AlertConditionResponse.model_validate(alert)


@router.put("/conditions/{alert_id}", response_model=AlertConditionResponse)
async def update_alert(
    alert_id: int,
    data: AlertConditionUpdate,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """更新预警条件"""
    alert = await service.update_alert(alert_id, current_user.id, data)
    if not alert:
        raise HTTPException(status_code=404, detail="预警不存在")
    return AlertConditionResponse.model_validate(alert)


@router.delete("/conditions/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """删除预警条件"""
    ok = await service.delete_alert(alert_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="预警不存在")


# --- Notifications ---

@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """获取通知列表"""
    notifs = await service.get_notifications(current_user.id, limit=limit)
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.patch("/notifications/{notif_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notif_id: int,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """标记通知已读"""
    ok = await service.mark_notification_read(notif_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="通知不存在")

    # 返回更新后的通知
    notifs = await service.get_notifications(current_user.id, limit=1)
    return NotificationResponse.model_validate(notifs[0]) if notifs else HTTPException(status_code=404)


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """获取未读通知数"""
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}
