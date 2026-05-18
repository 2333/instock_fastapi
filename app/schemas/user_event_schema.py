from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_ROUTE_NAMES = {
    "HomeWorkbench",
    "Selection",
    "Backtest",
    "StockDetail",
    "Attention",
}
ALLOWED_DASHBOARD_CARDS = {"market", "attention", "selection", "backtest"}
ALLOWED_DASHBOARD_TARGETS = {"/stocks", "/attention", "/selection", "/backtest"}
ALLOWED_FILTER_KEYS = {
    "priceMin",
    "priceMax",
    "changeMin",
    "changeMax",
    "market",
    "rsiMin",
    "rsiMax",
    "macdBullish",
    "macdBearish",
    "pattern",
}


def _normalize_string(value: Any, *, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be blank")
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return cleaned


def _normalize_optional_string(value: Any, *, field_name: str, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return cleaned


def _normalize_int(
    value: Any,
    *,
    field_name: str,
    min_value: int = 0,
    max_value: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    if value < min_value:
        raise ValueError(f"{field_name} must be greater than or equal to {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{field_name} must be less than or equal to {max_value}")
    return value


def _normalize_string_list(
    value: Any,
    *,
    field_name: str,
    item_max_length: int,
    max_items: int,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be an array")
    if len(value) > max_items:
        raise ValueError(f"{field_name} must contain at most {max_items} items")

    cleaned: list[str] = []
    for item in value:
        cleaned.append(
            _normalize_string(item, field_name=f"{field_name} item", max_length=item_max_length)
        )
    return cleaned


class EventDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageViewEventData(EventDataModel):
    route_name: str

    @field_validator("route_name", mode="before")
    @classmethod
    def validate_route_name(cls, value: Any) -> str:
        cleaned = _normalize_string(value, field_name="route_name", max_length=120)
        if cleaned not in ALLOWED_ROUTE_NAMES:
            raise ValueError("Unsupported route_name")
        return cleaned


class DashboardCardClickEventData(EventDataModel):
    card: str
    target_path: str

    @field_validator("card", mode="before")
    @classmethod
    def validate_card(cls, value: Any) -> str:
        cleaned = _normalize_string(value, field_name="card", max_length=50)
        if cleaned not in ALLOWED_DASHBOARD_CARDS:
            raise ValueError("Unsupported dashboard card")
        return cleaned

    @field_validator("target_path", mode="before")
    @classmethod
    def validate_target_path(cls, value: Any) -> str:
        cleaned = _normalize_string(value, field_name="target_path", max_length=120)
        if cleaned not in ALLOWED_DASHBOARD_TARGETS:
            raise ValueError("Unsupported dashboard target_path")
        return cleaned


class FilterRunEventData(EventDataModel):
    filter_keys: list[str]
    filter_count: int
    market: str | None = None
    result_count: int
    trade_date: str | None = None

    @field_validator("filter_keys", mode="before")
    @classmethod
    def validate_filter_keys(cls, value: Any) -> list[str]:
        cleaned = _normalize_string_list(
            value,
            field_name="filter_keys",
            item_max_length=50,
            max_items=50,
        )
        unsupported = sorted({item for item in cleaned if item not in ALLOWED_FILTER_KEYS})
        if unsupported:
            raise ValueError(f"Unsupported filter_keys: {', '.join(unsupported)}")
        return cleaned

    @field_validator("filter_count", mode="before")
    @classmethod
    def validate_filter_count(cls, value: Any) -> int:
        return _normalize_int(value, field_name="filter_count", max_value=1000)

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, value: Any) -> str | None:
        return _normalize_optional_string(value, field_name="market", max_length=50)

    @field_validator("result_count", mode="before")
    @classmethod
    def validate_result_count(cls, value: Any) -> int:
        return _normalize_int(value, field_name="result_count", max_value=100000)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> str | None:
        return _normalize_optional_string(value, field_name="trade_date", max_length=16)

    @model_validator(mode="after")
    def validate_filter_count_matches_keys(self) -> "FilterRunEventData":
        if self.filter_count != len(self.filter_keys):
            raise ValueError("filter_count must match filter_keys length")
        return self


class BacktestRunEventData(EventDataModel):
    strategy: str
    stock_code: str
    period: str
    start_date: str
    end_date: str
    param_keys: list[str]

    @field_validator("strategy", mode="before")
    @classmethod
    def validate_strategy(cls, value: Any) -> str:
        return _normalize_string(value, field_name="strategy", max_length=100)

    @field_validator("stock_code", mode="before")
    @classmethod
    def validate_stock_code(cls, value: Any) -> str:
        return _normalize_string(value, field_name="stock_code", max_length=20)

    @field_validator("period", mode="before")
    @classmethod
    def validate_period(cls, value: Any) -> str:
        return _normalize_string(value, field_name="period", max_length=50)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_dates(cls, value: Any, info) -> str:
        return _normalize_string(value, field_name=info.field_name, max_length=16)

    @field_validator("param_keys", mode="before")
    @classmethod
    def validate_param_keys(cls, value: Any) -> list[str]:
        return _normalize_string_list(
            value,
            field_name="param_keys",
            item_max_length=50,
            max_items=50,
        )


class PatternViewEventData(EventDataModel):
    stock_code: str
    pattern_name: str
    pattern_type: str
    confidence: int
    trade_date: str

    @field_validator("stock_code", mode="before")
    @classmethod
    def validate_stock_code(cls, value: Any) -> str:
        return _normalize_string(value, field_name="stock_code", max_length=20)

    @field_validator("pattern_name", mode="before")
    @classmethod
    def validate_pattern_name(cls, value: Any) -> str:
        return _normalize_string(value, field_name="pattern_name", max_length=100)

    @field_validator("pattern_type", mode="before")
    @classmethod
    def validate_pattern_type(cls, value: Any) -> str:
        return _normalize_string(value, field_name="pattern_type", max_length=50)

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, value: Any) -> int:
        return _normalize_int(value, field_name="confidence", max_value=100)

    @field_validator("trade_date", mode="before")
    @classmethod
    def validate_trade_date(cls, value: Any) -> str:
        return _normalize_string(value, field_name="trade_date", max_length=16)


class AttentionActionEventData(EventDataModel):
    action: Literal["add", "remove", "update"]
    stock_code: str
    source: Literal["stock_detail", "attention_page"]

    @field_validator("stock_code", mode="before")
    @classmethod
    def validate_stock_code(cls, value: Any) -> str:
        return _normalize_string(value, field_name="stock_code", max_length=20)


EVENT_DATA_SCHEMAS: dict[str, type[EventDataModel]] = {
    "page_view": PageViewEventData,
    "dashboard_card_click": DashboardCardClickEventData,
    "filter_run": FilterRunEventData,
    "backtest_run": BacktestRunEventData,
    "pattern_view": PatternViewEventData,
    "attention_action": AttentionActionEventData,
}


class UserEventTrackRequest(BaseModel):
    event_type: str
    page: str
    referrer: str | None = None
    event_data: dict[str, Any]

    model_config = ConfigDict(extra="forbid")

    @field_validator("event_type", mode="before")
    @classmethod
    def validate_event_type(cls, value: Any) -> str:
        cleaned = _normalize_string(value, field_name="event_type", max_length=50)
        if cleaned not in EVENT_DATA_SCHEMAS:
            raise ValueError("Unsupported event_type")
        return cleaned

    @field_validator("page", mode="before")
    @classmethod
    def validate_page(cls, value: Any) -> str:
        return _normalize_string(value, field_name="page", max_length=120)

    @field_validator("referrer", mode="before")
    @classmethod
    def validate_referrer(cls, value: Any) -> str | None:
        return _normalize_optional_string(value, field_name="referrer", max_length=255)

    @field_validator("event_data", mode="before")
    @classmethod
    def validate_event_data_is_object(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("event_data must be an object")
        return value

    @model_validator(mode="after")
    def validate_event_data_schema(self) -> "UserEventTrackRequest":
        schema = EVENT_DATA_SCHEMAS[self.event_type]
        validated = schema.model_validate(self.event_data)
        self.event_data = validated.model_dump(exclude_none=True)
        return self


class UserEventTrackResponse(BaseModel):
    accepted: bool = True
    persisted: bool = Field(...)
