import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.alert_models import AlertCondition, Notification
from app.models.stock_model import DailyBar
from app.services.alert_service import AlertService, COOLDOWN_HOURS

logger = logging.getLogger(__name__)


async def fetch_latest_price(session: AsyncSession, code: str) -> Decimal | None:
    """获取股票最新收盘价"""
    result = await session.execute(
        select(DailyBar.close, DailyBar.trade_date)
        .where(DailyBar.code == code)
        .order_by(DailyBar.trade_date.desc())
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


async def fetch_latest_rsi(session: AsyncSession, code: str) -> Decimal | None:
    """获取股票最新 RSI（假设存在 indicator 表）"""
    from app.models.stock_model import Indicator

    result = await session.execute(
        select(Indicator.rsi_6)
        .where(Indicator.code == code)
        .order_by(Indicator.trade_date.desc())
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


async def check_single_alert(session: AsyncSession, alert: AlertCondition, service: AlertService) -> bool:
    """检查单个预警条件是否触发"""
    code = alert.code
    cond = alert.condition
    cond_type = cond.get("type")

    current_value: Decimal | None = None

    if cond_type == "price":
        current_value = await fetch_latest_price(session, code)
    elif cond_type == "rsi":
        current_value = await fetch_latest_rsi(session, code)
    # TODO: 扩展其他类型（change/pattern/fund）

    if current_value is None:
        return False

    triggered = await service.should_trigger(alert, float(current_value))
    if triggered:
        # 更新触发时间
        await service.mark_triggered(alert)

        # 创建通知
        title = f"预警触发：{alert.name}"
        message = f"{code} {cond_type} 当前值 {current_value} 达到预警条件"
        await service.create_notification(
            user_id=alert.user_id,
            type="alert",
            title=title,
            message=message,
            payload={"alert_id": alert.id, "code": code, "condition": cond},
        )
        logger.info("Alert triggered: user=%s code=%s type=%s", alert.user_id, code, cond_type)
        return True

    return False


async def check_all_alerts():
    """检查所有活跃预警（定时任务入口）"""
    logger.info("Starting alert check cycle...")
    async with async_session_factory() as session:
        # 查询所有活跃预警
        result = await session.execute(
            select(AlertCondition).where(AlertCondition.is_active == True)
        )
        alerts = list(result.scalars().all())

        if not alerts:
            logger.info("No active alerts found.")
            return

        service = AlertService(session)
        triggered_count = 0

        for alert in alerts:
            try:
                triggered = await check_single_alert(session, alert, service)
                if triggered:
                    triggered_count += 1
            except Exception as e:
                logger.error("Failed to check alert %s: %s", alert.id, e, exc_info=True)

        await session.commit()
        logger.info("Alert check cycle completed: %d/%d triggered", triggered_count, len(alerts))


# 开发环境手动触发端点（生产环境接入 Celery Beat）
async def trigger_alert_check():
    """手动触发预警检查（用于开发/测试）"""
    await check_all_alerts()
