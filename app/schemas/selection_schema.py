"""Selection and screening API schemas for Phase 0 Milestone 1.

This module keeps backward-compatible selection contracts while introducing a
screening-first schema that is more structured and can carry minimal reason and
evidence summaries for each result.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ScreeningScope(BaseModel):
    """Execution scope for a screening run."""

    market: str | None = Field(
        None, description="Market scope: 'sh' for Shanghai, 'sz' for Shenzhen"
    )
    limit: int = Field(300, ge=1, le=500)

    model_config = ConfigDict(populate_by_name=True)


class ScreeningConditionMatch(BaseModel):
    """Minimal summary for one matched screening condition."""

    field: str
    operator: str
    value: str | int | float | bool
    summary: str


class ScreeningEvidenceItem(BaseModel):
    """Minimal evidence attached to one screening result."""

    metric: str
    value: str | int | float | bool | None = None
    summary: str


class ScreeningReason(BaseModel):
    """Human-readable explanation for why a result matched."""

    summary: str | None = None
    matched: list[ScreeningConditionMatch] = Field(default_factory=list)
    evidence: list[ScreeningEvidenceItem] = Field(default_factory=list)


class ScreeningRequest(BaseModel):
    """Canonical request body for screening endpoints.

    Backward compatibility:
    - ``conditions`` maps into ``filters``
    - legacy callers may still pass only ``conditions``
    """

    filters: SelectionFilters = Field(default_factory=SelectionFilters)
    scope: ScreeningScope = Field(default_factory=ScreeningScope)
    conditions: SelectionFilters | dict[str, Any] | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_conditions(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw_filters = data.get("filters")
        raw_conditions = data.get("conditions")
        if raw_filters is None and raw_conditions is not None:
            data = dict(data)
            data["filters"] = raw_conditions

        return data


class SelectionRequest(ScreeningRequest):
    """Backward-compatible request body for POST /selection."""


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
    reason_summary: str | None = Field(
        None, description="Minimal human-readable reason summary for the match"
    )
    reason: ScreeningReason | None = Field(
        None, description="Optional structured reason/evidence payload"
    )


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
    reason_summary: str | None = Field(
        None, description="Minimal human-readable reason summary when available"
    )


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


class ScreeningFilterField(BaseModel):
    """Metadata for one supported filter field."""

    key: str
    label: str
    value_type: str
    operators: list[str]


class ScreeningMetadata(BaseModel):
    """Structured metadata for clients building screening UIs."""

    markets: list[str]
    indicators: list[str]
    strategies: list[str]
    filter_fields: list[ScreeningFilterField] = Field(default_factory=list)


class ScreeningMetadataResponse(BaseModel):
    """Canonical response for screening metadata."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: ScreeningMetadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScreeningQuery(BaseModel):
    """Echo of the resolved screening query."""

    filters: SelectionFilters = Field(default_factory=SelectionFilters)
    scope: ScreeningScope = Field(default_factory=ScreeningScope)
    trade_date: str | None = None


class ScreeningRunData(BaseModel):
    """Structured data payload for a screening run."""

    query: ScreeningQuery
    items: list[SelectionResultItem] = Field(default_factory=list)
    total: int = 0


class ScreeningRunResponse(BaseModel):
    """Canonical response for POST /screening/run."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: ScreeningRunData
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScreeningHistoryData(BaseModel):
    """Structured payload for screening history queries."""

    trade_date: str | None = None
    limit: int
    items: list[SelectionHistoryItem] = Field(default_factory=list)
    total: int = 0


class ScreeningHistoryResponse(BaseModel):
    """Canonical response for GET /screening/history."""

    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: ScreeningHistoryData
    timestamp: datetime = Field(default_factory=datetime.utcnow)
