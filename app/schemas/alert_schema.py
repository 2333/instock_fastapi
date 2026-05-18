"""Alert engine schema contracts for the M3 P3-03 baseline."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


def _normalize_ts_code(value: Any, _: ValidationInfo) -> str:
    if value is None:
        raise ValueError("ts_code cannot be empty")
    if not isinstance(value, str):
        raise ValueError("ts_code must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("ts_code cannot be empty")
    if len(cleaned) > 20:
        raise ValueError("ts_code must be 20 characters or fewer")
    return cleaned


class AlertRuleBase(BaseModel):
    """Shared alert rule fields for the baseline rule contract."""

    ts_code: str = Field(..., description="Market-qualified stock code, e.g. 000001.SZ")
    rule_type: Literal["price_above", "price_below", "change_above", "change_below"]
    threshold: float
    cooldown_minutes: int = Field(default=60, ge=0, le=60 * 24 * 7)
    is_active: bool = True

    @field_validator("ts_code")
    @classmethod
    def normalize_ts_code(cls, value: Any, info: ValidationInfo) -> str:
        return _normalize_ts_code(value, info)


class AlertRuleCreate(AlertRuleBase):
    """Request body to create a rule."""


class AlertRuleUpdate(BaseModel):
    """Patch payload for an existing alert rule."""

    ts_code: str | None = None
    rule_type: Literal["price_above", "price_below", "change_above", "change_below"] | None = (
        None
    )
    threshold: float | None = None
    cooldown_minutes: int | None = Field(default=None, ge=0, le=60 * 24 * 7)
    is_active: bool | None = None

    @field_validator("ts_code")
    @classmethod
    def normalize_ts_code(cls, value: Any, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        return _normalize_ts_code(value, info)


class AlertRule(AlertRuleBase):
    """Read model for a persisted alert rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AlertRuleListResponse(BaseModel):
    """Envelope for alert rule list endpoints."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[AlertRule] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AlertRuleResponse(BaseModel):
    """Envelope for alert rule create/update endpoints."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: AlertRule | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NotificationItem(BaseModel):
    """Application notification row exposed via list APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    alert_condition_id: int | None = None
    ts_code: str
    title: str | None = None
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    is_read: bool = False
    created_at: datetime | None = None
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    """Envelope for notification read/list endpoints."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[NotificationItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarkNotificationReadRequest(BaseModel):
    """Payload to mark one notification as read/unread."""

    is_read: bool = True
