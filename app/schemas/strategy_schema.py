from typing import Any

from pydantic import BaseModel, Field


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
    default_params: dict[str, Any] = Field(default_factory=dict)
    parameters: list[StrategyTemplateParamResponse] = Field(default_factory=list)


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
