from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ParameterSpace(BaseModel):
    """参数空间定义"""
    type: str = Field(..., description="参数类型: int/float")
    low: float = Field(..., description="下界")
    high: float = Field(..., description="上界")
    step: Optional[float] = Field(None, description="步长（int 类型可选）")


class OptimizationJobCreate(BaseModel):
    """创建优化任务"""
    strategy_type: str = Field(..., description="策略类型")
    parameter_space: Dict[str, ParameterSpace] = Field(..., description="参数空间")
    optimization_method: str = Field(default="random", description="优化方法: random/bayesian")
    objective_metric: str = Field(default="sharpe_ratio", description="目标指标")
    total_trials: int = Field(default=100, ge=1, le=1000, description="总试验次数")
    max_parallel: int = Field(default=4, ge=1, le=20, description="最大并发数")
    stock_code: Optional[str] = Field(None, description="回测股票代码（可选）")
    start_date: Optional[str] = Field(None, description="回测开始日期")
    end_date: Optional[str] = Field(None, description="回测结束日期")
    initial_capital: float = Field(default=100000, description="初始资金")


class OptimizationJobResponse(BaseModel):
    """优化任务响应"""
    id: int
    user_id: int
    strategy_type: str
    parameter_space: Dict[str, Any]
    optimization_method: str
    objective_metric: str
    total_trials: int
    completed_trials: int
    status: str
    error_message: Optional[str] = None
    best_parameters: Optional[Dict[str, Any]] = None
    best_score: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OptimizationTrialResponse(BaseModel):
    """试验记录响应"""
    id: int
    job_id: int
    parameters: Dict[str, Any]
    score: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    backtest_result_id: Optional[int] = None
    status: str
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OptimizationProgress(BaseModel):
    """优化进度"""
    job_id: int
    status: str
    completed_trials: int
    total_trials: int
    progress_percent: float
    best_score: Optional[float] = None
    best_parameters: Optional[Dict[str, Any]] = None
