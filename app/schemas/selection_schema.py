"""Selection API schemas for Phase A - Contract Definition.

This module defines typed request/response schemas for the selection API.
Phase A focuses on minimal contract definition without complex evidence/reason fields.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SelectionFilters(BaseModel):
    """Request filters for stock selection.

    All fields are optional. Absent fields mean "no filter" for that dimension.
    """

    price_min: float | None = Field(None, alias="priceMin")
    price_max: float | None = Field(None, alias="priceMax")
    change_min: float | None = Field(None, alias="changeMin")
    change_max: float | None = Field(None, alias="changeMax")
    market: str | None = Field(
        None, description="Market filter: 'sh' for Shanghai, 'sz' for Shenzhen"
    )

    model_config = ConfigDict(populate_by_name=True)


class SelectionRequest(BaseModel):
    """Request body for POST /selection endpoint.

    Legacy support: accepts raw dict for backward compatibility,
    but typed fields are preferred.
    """

    conditions: SelectionFilters | dict[str, Any] = Field(default_factory=dict)


class SelectionResultItem(BaseModel):
    """Single selection result item.

    Represents one stock that matched the selection criteria.
    """

    ts_code: str
    code: str
    stock_name: str
    trade_date: str
    date: str  # Mirror of trade_date for convenience
    close: float
    change_rate: float
    amount: float
    score: float
    signal: str  # "buy", "sell", or "hold"
    # Phase B extension placeholder: reason/evidence fields can be added here
    reason: str | None = Field(None, description="Optional reasoning (extensible for Phase B)")


class SelectionResponse(BaseModel):
    """Response wrapper for selection results.

    Standard envelope with typed items array.
    """

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[SelectionResultItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SelectionHistoryItem(BaseModel):
    """Single history result item from selection_results table."""

    selection_id: str
    ts_code: str
    code: str
    stock_name: str | None
    trade_date: str
    date: str  # Mirror of trade_date for convenience
    score: float
    signal: str  # Always "hold" for history items


class SelectionHistoryResponse(BaseModel):
    """Response wrapper for selection history."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[SelectionHistoryItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SelectionConditionCreate(BaseModel):
    """Request to create/update a saved selection condition."""

    name: str
    category: str
    description: str | None = None
    params: dict[str, Any] | None = None
    is_active: bool = True


class SelectionConditionResponse(BaseModel):
    """Response for a saved selection condition (ORM-backed)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    category: str
    description: str | None
    params: dict[str, Any] | None
    is_active: bool


class SelectionConditionsMetaResponse(BaseModel):
    """Response for GET /selection/conditions (static metadata)."""

    markets: list[str]
    indicators: list[str]
    strategies: list[str]
