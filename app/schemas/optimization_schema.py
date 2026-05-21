"""Parameter optimization API schemas for M5 / P3-05."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OptimizationMetric = Literal["sharpe_ratio", "total_return", "max_drawdown"]
OptimizationDirection = Literal["maximize", "minimize"]
OptimizationStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class ParameterOptimizationJobCreate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    base_params: dict[str, Any] = Field(..., min_length=1)
    parameter_space: dict[str, Any] = Field(..., min_length=1, max_length=8)
    method: Literal["random_search"] = "random_search"
    objective_metric: OptimizationMetric = "sharpe_ratio"
    objective_direction: OptimizationDirection | None = None
    trial_count: int = Field(default=10, ge=1, le=50)
    random_seed: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def set_default_direction(self) -> "ParameterOptimizationJobCreate":
        if self.objective_direction is None:
            self.objective_direction = (
                "minimize" if self.objective_metric == "max_drawdown" else "maximize"
            )
        return self


class ParameterOptimizationJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str | None = None
    method: Literal["random_search"] = "random_search"
    status: OptimizationStatus
    progress: int = 0
    base_params: dict[str, Any]
    parameter_space: dict[str, Any]
    objective_metric: OptimizationMetric
    objective_direction: OptimizationDirection
    trial_count: int
    completed_trials: int = 0
    failed_trials: int = 0
    random_seed: int | None = None
    best_trial_id: int | None = None
    best_parameters: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score: float | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ParameterOptimizationTrialItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    trial_index: int
    status: OptimizationStatus
    params: dict[str, Any]
    metrics: dict[str, Any] | None = None
    score: float | None = None
    backtest_result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ParameterOptimizationBestItem(BaseModel):
    job_id: int
    status: OptimizationStatus
    best_trial_id: int | None = None
    best_parameters: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score: float | None = None
    backtest_params: dict[str, Any] | None = None


class ParameterOptimizationJobResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: ParameterOptimizationJobItem | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ParameterOptimizationJobListResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[ParameterOptimizationJobItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ParameterOptimizationTrialListResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[ParameterOptimizationTrialItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ParameterOptimizationBestResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: ParameterOptimizationBestItem
    timestamp: datetime = Field(default_factory=datetime.utcnow)
