from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import User
from app.schemas.alert_subscription_schema import (
    AlertSubscriptionCreate,
    AlertSubscriptionListResponse,
    AlertSubscriptionResponse,
    AlertSubscriptionRunResponse,
    MarkNotificationReadRequest,
    NotificationListResponse,
)
from app.services.alert_subscription_service import AlertSubscriptionService

router = APIRouter()


@router.get("/alerts/subscriptions", response_model=AlertSubscriptionListResponse)
async def list_alert_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertSubscriptionListResponse:
    service = AlertSubscriptionService(db)
    return AlertSubscriptionListResponse(data=await service.list_subscriptions(current_user.id))


@router.post("/alerts/subscriptions", response_model=AlertSubscriptionResponse)
async def create_alert_subscription(
    payload: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertSubscriptionResponse:
    service = AlertSubscriptionService(db)
    return AlertSubscriptionResponse(
        data=await service.create_subscription(user_id=current_user.id, payload=payload)
    )


@router.post("/alerts/subscriptions/{subscription_id}/run", response_model=AlertSubscriptionRunResponse)
async def run_alert_subscription(
    subscription_id: int,
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertSubscriptionRunResponse:
    service = AlertSubscriptionService(db)
    return AlertSubscriptionRunResponse(
        data=await service.run_subscription(
            user_id=current_user.id,
            subscription_id=subscription_id,
            date=date,
        )
    )


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    service = AlertSubscriptionService(db)
    return NotificationListResponse(data=await service.list_notifications(current_user.id))


@router.patch("/notifications/{notification_id}", response_model=NotificationListResponse)
async def mark_notification_read(
    notification_id: int,
    payload: MarkNotificationReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    service = AlertSubscriptionService(db)
    item = await service.mark_notification_read(
        user_id=current_user.id,
        notification_id=notification_id,
        is_read=payload.is_read,
    )
    return NotificationListResponse(data=[item])
