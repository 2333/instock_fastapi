"""Alert subscription schemas for M3-B subscription baseline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AlertSubscriptionCreate(BaseModel):
    selection_condition_id: int = Field(..., ge=1)
    name: str | None = Field(default=None, max_length=100)
    schedule_type: Literal["post_close"] = "post_close"
    cooldown_trade_days: int = Field(default=1, ge=0, le=30)


class AlertSubscriptionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    selection_condition_id: int
    selection_condition_name: str | None = None
    name: str | None = None
    schedule_type: Literal["post_close"] = "post_close"
    cooldown_trade_days: int = 1
    definition_version: int
    definition_hash: str
    status: Literal["active", "paused", "stale"] = "active"
    stale_reason: str | None = None
    last_run_trade_date: str | None = None
    last_run_at: datetime | None = None
    last_notified_trade_date: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlertSubscriptionListResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[AlertSubscriptionItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AlertSubscriptionResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: AlertSubscriptionItem | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AlertRunHitItem(BaseModel):
    ts_code: str
    trade_date: str
    rank: int = 0
    score: float | None = None
    signal: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class AlertRunItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    selection_condition_id: int
    trade_date: str
    definition_version: int
    definition_hash: str
    status: Literal["completed", "skipped"] = "completed"
    match_count: int = 0
    new_match_count: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)
    notification_id: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    ts_code: str
    title: str | None = None
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    is_read: bool = False
    alert_condition_id: int | None = None
    subscription_id: int | None = None
    alert_run_id: int | None = None
    notification_type: str | None = None
    dedupe_key: str | None = None
    created_at: datetime | None = None
    read_at: datetime | None = None


class AlertSubscriptionRunResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NotificationListResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[NotificationItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarkNotificationReadRequest(BaseModel):
    is_read: bool = True
