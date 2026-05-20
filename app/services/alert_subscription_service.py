"""Services for M3-B alert subscriptions and manual trigger runtime."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.stock_model import (
    AlertRun,
    AlertRunHit,
    AlertSubscription,
    Notification,
    SelectionCondition,
)
from app.services.date_utils import parse_trade_date
from app.schemas.alert_subscription_schema import (
    AlertRunHitItem,
    AlertRunItem,
    AlertSubscriptionCreate,
    AlertSubscriptionItem,
    NotificationItem,
)
from app.services.selection_service import SelectionService


class AlertSubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _status_literal(status: str | None) -> str:
        if status in {"active", "paused", "stale"}:
            return status
        return "active"

    @staticmethod
    def _run_status_literal(status: str | None) -> str:
        if status in {"completed", "skipped"}:
            return status
        return "completed"

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _is_notification_in_cooldown(
        *,
        last_notified_trade_date: str | None,
        current_trade_date: str,
        cooldown_trade_days: int,
    ) -> bool:
        if cooldown_trade_days <= 0 or not last_notified_trade_date:
            return False
        last_notified = parse_trade_date(last_notified_trade_date)
        current = parse_trade_date(current_trade_date)
        if last_notified is None or current is None or current <= last_notified:
            return False
        return (current - last_notified).days < cooldown_trade_days

    @staticmethod
    def _serialize_subscription(
        subscription: AlertSubscription,
        selection_condition_name: str | None = None,
    ) -> AlertSubscriptionItem:
        return AlertSubscriptionItem(
            id=subscription.id,
            user_id=subscription.user_id,
            selection_condition_id=subscription.selection_condition_id,
            selection_condition_name=selection_condition_name,
            name=subscription.name,
            schedule_type="post_close",
            cooldown_trade_days=subscription.cooldown_trade_days,
            definition_version=subscription.definition_version,
            definition_hash=subscription.definition_hash,
            status=AlertSubscriptionService._status_literal(subscription.status),  # type: ignore[arg-type]
            stale_reason=subscription.stale_reason,
            last_run_trade_date=subscription.last_run_trade_date,
            last_run_at=subscription.last_run_at,
            last_notified_trade_date=subscription.last_notified_trade_date,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    @staticmethod
    def _serialize_run(run: AlertRun) -> AlertRunItem:
        return AlertRunItem(
            id=run.id,
            subscription_id=run.subscription_id,
            selection_condition_id=run.selection_condition_id,
            trade_date=run.trade_date,
            definition_version=run.definition_version,
            definition_hash=run.definition_hash,
            status=AlertSubscriptionService._run_status_literal(run.status),  # type: ignore[arg-type]
            match_count=run.match_count,
            new_match_count=run.new_match_count,
            summary=run.summary or {},
            notification_id=run.notification_id,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )

    @staticmethod
    def _serialize_notification(notification: Notification | None) -> NotificationItem | None:
        if notification is None:
            return None
        return NotificationItem(
            id=notification.id,
            user_id=notification.user_id,
            ts_code=notification.ts_code,
            title=notification.title,
            message=notification.message,
            payload=notification.payload or {},
            is_read=notification.is_read,
            alert_condition_id=notification.alert_condition_id,
            subscription_id=getattr(notification, "subscription_id", None),
            alert_run_id=getattr(notification, "alert_run_id", None),
            notification_type=getattr(notification, "notification_type", None),
            dedupe_key=getattr(notification, "dedupe_key", None),
            created_at=notification.created_at,
            read_at=notification.read_at,
        )

    @staticmethod
    def _serialize_hit(hit: AlertRunHit) -> AlertRunHitItem:
        evidence = hit.evidence if isinstance(hit.evidence, list) else []
        return AlertRunHitItem(
            ts_code=hit.ts_code,
            trade_date=hit.trade_date,
            rank=hit.rank,
            score=AlertSubscriptionService._to_float(hit.score),
            signal=hit.signal,
            snapshot=hit.snapshot or {},
            evidence=evidence,
        )

    async def _get_selection_condition(
        self,
        *,
        user_id: int,
        selection_condition_id: int,
        lock: bool = False,
    ) -> SelectionCondition:
        stmt = select(SelectionCondition).where(
            SelectionCondition.id == selection_condition_id,
            SelectionCondition.user_id == user_id,
        )
        if lock:
            stmt = stmt.with_for_update()
        condition = (await self.db.execute(stmt)).scalar_one_or_none()
        if not condition:
            raise HTTPException(status_code=404, detail="筛选器不存在")
        return condition

    async def _find_duplicate_subscription(
        self,
        *,
        user_id: int,
        selection_condition_id: int,
        definition_hash: str,
    ) -> AlertSubscription | None:
        duplicate_stmt = select(AlertSubscription).where(
            AlertSubscription.user_id == user_id,
            AlertSubscription.selection_condition_id == selection_condition_id,
            AlertSubscription.definition_hash == definition_hash,
            AlertSubscription.schedule_type == "post_close",
        )
        return (await self.db.execute(duplicate_stmt)).scalar_one_or_none()

    async def list_subscriptions(self, user_id: int) -> list[AlertSubscriptionItem]:
        stmt = (
            select(AlertSubscription, SelectionCondition.name)
            .outerjoin(
                SelectionCondition,
                SelectionCondition.id == AlertSubscription.selection_condition_id,
            )
            .where(AlertSubscription.user_id == user_id)
            .order_by(AlertSubscription.updated_at.desc(), AlertSubscription.id.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            self._serialize_subscription(subscription, selection_condition_name=name)
            for subscription, name in rows
        ]

    async def create_subscription(
        self,
        *,
        user_id: int,
        payload: AlertSubscriptionCreate,
    ) -> AlertSubscriptionItem:
        condition = await self._get_selection_condition(
            user_id=user_id,
            selection_condition_id=payload.selection_condition_id,
        )
        if not condition.is_active:
            raise HTTPException(status_code=400, detail="筛选器已停用，不能创建订阅")

        definition_hash = condition.definition_hash or ""
        duplicate = await self._find_duplicate_subscription(
            user_id=user_id,
            selection_condition_id=payload.selection_condition_id,
            definition_hash=definition_hash,
        )
        if duplicate:
            if duplicate.status in {"active", "paused"}:
                raise HTTPException(status_code=400, detail="当前筛选器版本已存在订阅")
            duplicate.name = payload.name or condition.name
            duplicate.cooldown_trade_days = payload.cooldown_trade_days
            duplicate.definition_version = condition.definition_version
            duplicate.definition_hash = definition_hash
            duplicate.status = "active"
            duplicate.stale_reason = None
            duplicate.updated_at = datetime.utcnow()
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                raise HTTPException(status_code=400, detail="当前筛选器版本已存在订阅") from None
            await self.db.refresh(duplicate)
            return self._serialize_subscription(duplicate, selection_condition_name=condition.name)

        subscription = AlertSubscription(
            user_id=user_id,
            selection_condition_id=payload.selection_condition_id,
            name=payload.name or condition.name,
            schedule_type="post_close",
            cooldown_trade_days=payload.cooldown_trade_days,
            definition_version=condition.definition_version,
            definition_hash=definition_hash,
            status="active",
        )
        self.db.add(subscription)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            duplicate = await self._find_duplicate_subscription(
                user_id=user_id,
                selection_condition_id=payload.selection_condition_id,
                definition_hash=definition_hash,
            )
            if duplicate:
                raise HTTPException(status_code=400, detail="当前筛选器版本已存在订阅") from None
            raise
        await self.db.refresh(subscription)
        return self._serialize_subscription(subscription, selection_condition_name=condition.name)

    async def get_subscription(
        self,
        *,
        user_id: int,
        subscription_id: int,
        lock: bool = False,
    ) -> AlertSubscription:
        stmt = select(AlertSubscription).where(
            AlertSubscription.id == subscription_id,
            AlertSubscription.user_id == user_id,
        )
        if lock:
            stmt = stmt.with_for_update()
        subscription = (await self.db.execute(stmt)).scalar_one_or_none()
        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return subscription

    async def _mark_subscription_stale(
        self,
        *,
        subscription: AlertSubscription,
        reason: str,
    ) -> None:
        subscription.status = "stale"
        subscription.stale_reason = reason
        subscription.updated_at = datetime.utcnow()
        await self.db.flush()

    async def _ensure_subscription_current(
        self,
        *,
        subscription: AlertSubscription,
        lock: bool = False,
    ) -> SelectionCondition:
        if subscription.status == "stale":
            raise HTTPException(status_code=409, detail=subscription.stale_reason or "订阅已失效")
        condition = await self._get_selection_condition(
            user_id=subscription.user_id,
            selection_condition_id=subscription.selection_condition_id,
            lock=lock,
        )
        if not condition.is_active:
            await self._mark_subscription_stale(
                subscription=subscription,
                reason="筛选器已停用，需要重新确认订阅",
            )
            await self.db.commit()
            raise HTTPException(status_code=409, detail="筛选器已停用，订阅已标记为 stale")
        if (
            condition.definition_version != subscription.definition_version
            or (condition.definition_hash or "") != subscription.definition_hash
        ):
            await self._mark_subscription_stale(
                subscription=subscription,
                reason="筛选器定义已变化，需要重新创建订阅",
            )
            await self.db.commit()
            raise HTTPException(status_code=409, detail="筛选器定义已变化，订阅已标记为 stale")
        return condition

    async def run_subscription(
        self,
        *,
        user_id: int,
        subscription_id: int,
        date: str | None = None,
    ) -> dict[str, Any]:
        subscription = await self.get_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
            lock=True,
        )
        if subscription.status == "paused":
            raise HTTPException(status_code=400, detail="订阅已暂停")

        condition = await self._ensure_subscription_current(subscription=subscription, lock=True)
        selection_service = SelectionService(self.db)

        existing_run = await self._find_existing_run(
            subscription=subscription,
            date=date,
            selection_service=selection_service,
        )
        if existing_run:
            return await self._build_run_response(existing_run, subscription)

        definition = condition.params or {}
        scope = dict(definition.get("scope") or {})
        limit = int(scope.get("limit") or 300)
        items = await selection_service.run_selection(
            conditions=definition,
            date=date,
            limit=limit,
            definition=definition,
        )
        condition = await self._ensure_subscription_current(subscription=subscription, lock=True)
        trade_date = items[0]["trade_date"] if items else await selection_service._resolve_trade_date(date)
        if not trade_date:
            raise HTTPException(status_code=400, detail="当前没有可用于运行订阅的交易日数据")

        previous_hit_codes = await self._load_previous_hit_codes(
            subscription.id,
            trade_date=trade_date,
        )
        subscription_id = subscription.id
        subscription_definition_hash = subscription.definition_hash
        current_codes = [str(item["ts_code"]) for item in items if item.get("ts_code")]
        new_codes = [code for code in current_codes if code not in previous_hit_codes]
        notification_in_cooldown = self._is_notification_in_cooldown(
            last_notified_trade_date=subscription.last_notified_trade_date,
            current_trade_date=trade_date,
            cooldown_trade_days=subscription.cooldown_trade_days,
        )

        try:
            run = AlertRun(
                subscription_id=subscription.id,
                user_id=user_id,
                selection_condition_id=condition.id,
                trade_date=trade_date,
                definition_version=subscription.definition_version,
                definition_hash=subscription.definition_hash,
                definition_snapshot=definition,
                status="completed",
                match_count=len(current_codes),
                new_match_count=len(new_codes),
                summary={
                    "selection_condition_id": condition.id,
                    "selection_condition_name": condition.name,
                    "total_matches": len(current_codes),
                    "new_matches": len(new_codes),
                    "sample_codes": current_codes[:5],
                    "new_codes": new_codes[:5],
                    "notification_suppressed": notification_in_cooldown,
                    "suppression_reason": "cooldown" if notification_in_cooldown else None,
                },
                completed_at=datetime.utcnow(),
            )
            self.db.add(run)
            await self.db.flush()

            for index, item in enumerate(items, start=1):
                self.db.add(
                    AlertRunHit(
                        run_id=run.id,
                        ts_code=str(item["ts_code"]),
                        trade_date=trade_date,
                        rank=index,
                        score=self._to_float(item.get("score")),
                        signal=item.get("signal"),
                        snapshot={
                            "code": item.get("code"),
                            "stock_name": item.get("stock_name"),
                            "close": item.get("close"),
                            "change_rate": item.get("change_rate"),
                            "reason_summary": item.get("reason_summary"),
                        },
                        evidence=item.get("evidence") or [],
                    )
                )
            await self.db.flush()

            notification: Notification | None = None
            if new_codes and not notification_in_cooldown:
                primary_code = new_codes[0]
                dedupe_key = (
                    f"alert_summary:{subscription.id}:{trade_date}:{subscription.definition_hash}"
                )
                notification = Notification(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    alert_run_id=run.id,
                    notification_type="alert_summary",
                    dedupe_key=dedupe_key,
                    ts_code=primary_code,
                    title=f"{subscription.name or condition.name} 命中新结果",
                    message=f"{subscription.name or condition.name} 在 {trade_date} 新增 {len(new_codes)} 只命中",
                    payload={
                        "selection_condition_id": condition.id,
                        "selection_condition_name": condition.name,
                        "subscription_id": subscription.id,
                        "alert_run_id": run.id,
                        "trade_date": trade_date,
                        "new_codes": new_codes[:20],
                        "total_matches": len(current_codes),
                        "new_match_count": len(new_codes),
                    },
                    is_read=False,
                )
                self.db.add(notification)
                await self.db.flush()
                run.notification_id = notification.id
                subscription.last_notified_trade_date = trade_date

            subscription.last_run_trade_date = trade_date
            subscription.last_run_at = datetime.utcnow()
            subscription.updated_at = datetime.utcnow()

            await self.db.commit()
            return await self._build_run_response(run, subscription, notification=notification)
        except IntegrityError:
            await self.db.rollback()
            recovered_subscription = await self.get_subscription(
                user_id=user_id,
                subscription_id=subscription_id,
            )
            recovered_run = await self._find_existing_run_by_trade_date(
                subscription_id=subscription_id,
                trade_date=trade_date,
                definition_hash=subscription_definition_hash,
            )
            if recovered_run is not None:
                return await self._build_run_response(recovered_run, recovered_subscription)
            raise

    async def _find_existing_run(
        self,
        *,
        subscription: AlertSubscription,
        date: str | None,
        selection_service: SelectionService,
    ) -> AlertRun | None:
        resolved_trade_date = await selection_service._resolve_trade_date(date)
        if not resolved_trade_date:
            return None
        stmt = select(AlertRun).where(
            AlertRun.subscription_id == subscription.id,
            AlertRun.trade_date == resolved_trade_date,
            AlertRun.definition_hash == subscription.definition_hash,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _load_previous_hit_codes(
        self,
        subscription_id: int,
        *,
        trade_date: str,
    ) -> set[str]:
        previous_run_stmt: Select[tuple[AlertRun]] = (
            select(AlertRun)
            .where(
                AlertRun.subscription_id == subscription_id,
                AlertRun.status == "completed",
                AlertRun.trade_date < trade_date,
            )
            .order_by(desc(AlertRun.trade_date), desc(AlertRun.completed_at), desc(AlertRun.id))
            .limit(1)
        )
        previous_run = (await self.db.execute(previous_run_stmt)).scalar_one_or_none()
        if not previous_run:
            return set()

        hit_stmt = select(AlertRunHit.ts_code).where(AlertRunHit.run_id == previous_run.id)
        return {str(code) for code in (await self.db.execute(hit_stmt)).scalars().all()}

    async def _find_existing_run_by_trade_date(
        self,
        *,
        subscription_id: int,
        trade_date: str,
        definition_hash: str,
    ) -> AlertRun | None:
        stmt = select(AlertRun).where(
            AlertRun.subscription_id == subscription_id,
            AlertRun.trade_date == trade_date,
            AlertRun.definition_hash == definition_hash,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _build_run_response(
        self,
        run: AlertRun,
        subscription: AlertSubscription,
        notification: Notification | None = None,
    ) -> dict[str, Any]:
        if notification is None and run.notification_id:
            notification_stmt = select(Notification).where(Notification.id == run.notification_id)
            notification = (await self.db.execute(notification_stmt)).scalar_one_or_none()

        hit_stmt = (
            select(AlertRunHit)
            .where(AlertRunHit.run_id == run.id)
            .order_by(AlertRunHit.rank.asc(), AlertRunHit.id.asc())
        )
        hits = (await self.db.execute(hit_stmt)).scalars().all()
        return {
            "subscription": self._serialize_subscription(subscription),
            "run": self._serialize_run(run),
            "hits": [self._serialize_hit(hit) for hit in hits],
            "notification": self._serialize_notification(notification),
        }

    async def list_notifications(self, user_id: int) -> list[NotificationItem]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [self._serialize_notification(row) for row in rows if row is not None]

    async def mark_notification_read(
        self,
        *,
        user_id: int,
        notification_id: int,
        is_read: bool,
    ) -> NotificationItem:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        notification = (await self.db.execute(stmt)).scalar_one_or_none()
        if not notification:
            raise HTTPException(status_code=404, detail="通知不存在")
        notification.is_read = is_read
        notification.read_at = datetime.utcnow() if is_read else None
        await self.db.commit()
        await self.db.refresh(notification)
        serialized = self._serialize_notification(notification)
        if serialized is None:  # pragma: no cover
            raise HTTPException(status_code=500, detail="通知序列化失败")
        return serialized

    @staticmethod
    async def mark_subscriptions_stale_for_screener(
        db: AsyncSession,
        *,
        selection_condition_id: int,
        reason: str,
    ) -> None:
        await db.execute(
            update(AlertSubscription)
            .where(
                AlertSubscription.selection_condition_id == selection_condition_id,
                AlertSubscription.status.in_(("active", "paused")),
            )
            .values(
                status="stale",
                stale_reason=reason,
                updated_at=datetime.utcnow(),
            )
        )
