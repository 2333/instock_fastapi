from typing import Any

from pydantic import BaseModel, Field

from app.schemas.selection_schema import ScreeningScope, SelectionFilters


class StrategyResponse(BaseModel):
    name: str
    display_name: str
    description: str | None = None


class StrategyTemplateParamOption(BaseModel):
    label: str
    value: str


class StrategyTemplateParamResponse(BaseModel):
    name: str
    label: str
    type: str = "number"
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[StrategyTemplateParamOption] | None = None


class StrategyTemplateResponse(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    source: str = "manual"
    default_params: dict[str, Any] = Field(default_factory=dict)
    selection_schema: dict[str, Any] | None = None
    entry_rules_template: dict[str, Any] = Field(default_factory=dict)
    exit_rules_template: dict[str, Any] = Field(default_factory=dict)
    parameters: list[StrategyTemplateParamResponse] = Field(default_factory=list)


class StrategyBacktestConfig(BaseModel):
    """Legacy backtest configuration kept inside the canonical strategy envelope."""

    strategy_type: str | None = None
    stock_code: str | None = None
    period: str | None = None
    initial_capital: float | None = None
    position_size: float | None = None
    max_position: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    min_hold_days: int | None = None
    commission_rate: float | None = None
    min_commission: float | None = None
    slippage: float | None = None


class StrategySelectionParams(BaseModel):
    """Canonical params envelope for strategy persistence."""

    source: str = "selection"
    template_name: str = "selection_bridge"
    selection_filters: SelectionFilters = Field(default_factory=SelectionFilters)
    selection_scope: ScreeningScope = Field(default_factory=ScreeningScope)
    entry_rules: dict[str, Any] = Field(default_factory=dict)
    exit_rules: dict[str, Any] = Field(default_factory=dict)
    backtest_config: StrategyBacktestConfig = Field(default_factory=StrategyBacktestConfig)
    strategy_params: dict[str, Any] = Field(default_factory=dict)


class StrategySelectionCreateRequest(BaseModel):
    """Request payload for saving current screening conditions as a strategy."""

    name: str
    description: str | None = None
    params: dict[str, Any] | StrategySelectionParams | None = None
    is_active: bool = True


class StrategyResultResponse(BaseModel):
    id: int
    date: str | None = None
    strategy_name: str | None = None
    code: str | None = None
    name: str | None = None
    score: float | None = None
    signal: str | None = None
    new_price: float | None = None
    change_rate: float | None = None
