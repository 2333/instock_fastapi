from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_models import AlertCondition, Notification
from app.schemas.alert_schema import AlertConditionCreate, AlertConditionUpdate


COOLDOWN_HOURS = 1  # 预警冷却时间


class AlertService:
    """预警规则服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(self, user_id: int, data: AlertConditionCreate) -> AlertCondition:
        """创建预警条件"""
        alert = AlertCondition(
            user_id=user_id,
            name=data.name,
            code=data.code,
            condition=data.condition,
            is_active=data.is_active,
            notify_channels=data.notify_channels,
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def get_user_alerts(self, user_id: int, active_only: bool = False) -> list[AlertCondition]:
        """查询用户预警列表"""
        stmt = select(AlertCondition).where(AlertCondition.user_id == user_id)
        if active_only:
            stmt = stmt.where(AlertCondition.is_active == True)
        stmt = stmt.order_by(AlertCondition.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_alert(self, alert_id: int, user_id: int) -> Optional[AlertCondition]:
        """查询单个预警（需归属当前用户）"""
        stmt = select(AlertCondition).where(
            AlertCondition.id == alert_id,
            AlertCondition.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_alert(self, alert_id: int, user_id: int, data: AlertConditionUpdate) -> Optional[AlertCondition]:
        """更新预警条件"""
        alert = await self.get_alert(alert_id, user_id)
        if not alert:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(alert, key, value)

        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """删除预警条件"""
        alert = await self.get_alert(alert_id, user_id)
        if not alert:
            return False

        await self.db.delete(alert)
        await self.db.flush()
        return True

    async def should_trigger(self, alert: AlertCondition, current_value: float) -> bool:
        """判断预警是否应触发"""
        if not alert.is_active:
            return False

        # 冷却检查
        if alert.last_triggered_at:
            cooldown = datetime.utcnow() - alert.last_triggered_at
            if cooldown < timedelta(hours=COOLDOWN_HOURS):
                return False

        cond = alert.condition
        operator = cond.get("operator")
        threshold = cond.get("value")

        if threshold is None:
            return False

        if operator == "gt":
            return current_value > threshold
        elif operator == "gte":
            return current_value >= threshold
        elif operator == "lt":
            return current_value < threshold
        elif operator == "lte":
            return current_value <= threshold
        else:
            return False

    async def mark_triggered(self, alert: AlertCondition):
        """标记预警已触发（更新 last_triggered_at）"""
        alert.last_triggered_at = datetime.utcnow()
        await self.db.flush()

    async def create_notification(
        self,
        user_id: int,
        type: str,
        title: str,
        message: str,
        payload: Optional[dict] = None,
    ) -> Notification:
        """创建应用内通知"""
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            payload=payload,
        )
        self.db.add(notif)
        await self.db.flush()
        await self.db.refresh(notif)
        return notif

    async def get_unread_count(self, user_id: int) -> int:
        """获取未读通知数"""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() or 0

    async def get_notifications(self, user_id: int, limit: int = 50) -> list[Notification]:
        """获取用户通知列表（按时间倒序）"""
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_notification_read(self, notif_id: int, user_id: int) -> bool:
        """标记通知已读"""
        stmt = (
            select(Notification)
            .where(Notification.id == notif_id, Notification.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        notif = result.scalar_one_or_none()
        if not notif:
            return False

        notif.is_read = True
        notif.read_at = datetime.utcnow()
        await self.db.flush()
        return True
