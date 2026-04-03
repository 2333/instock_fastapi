from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, Index, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.stock_model import Base


class ParameterOptimizationJob(Base):
    """参数优化任务模型"""
    __tablename__ = "parameter_optimization_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # 策略类型
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 参数空间定义
    parameter_space: Mapped[dict] = mapped_column(JSON, nullable=False, comment="参数边界定义")

    # 优化配置
    optimization_method: Mapped[str] = mapped_column(String(50), default="random", comment="优化方法: random/bayesian/genetic")
    objective_metric: Mapped[str] = mapped_column(String(50), default="sharpe_ratio", comment="目标指标: sharpe_ratio/total_return/max_drawdown")
    total_trials: Mapped[int] = mapped_column(Integer, default=100, comment="总试验次数")
    max_parallel: Mapped[int] = mapped_column(Integer, default=4, comment="最大并发数")

    # 进度状态
    completed_trials: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True, comment="pending/running/completed/failed/cancelled")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 最优结果
    best_parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="最优参数组合")
    best_score: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True, comment="最优目标指标值")
    best_backtest_result_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="最优结果对应的回测ID")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index('ix_optimization_jobs_user_status', 'user_id', 'status'),
        Index('ix_optimization_jobs_created', 'created_at'),
    )


class ParameterOptimizationTrial(Base):
    """单次优化试验记录"""
    __tablename__ = "parameter_optimization_trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("parameter_optimization_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # 试验参数
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, comment="本次试验的参数组合")

    # 回测结果
    backtest_result_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="关联的回测结果ID")
    score: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True, comment="目标指标值")

    # 元数据
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="完整指标: {total_return, sharpe, max_drawdown, win_rate...}")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息（如有）")

    # 状态与时间
    status: Mapped[str] = mapped_column(String(20), default="running", index=True, comment="running/completed/failed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index('ix_optimization_trials_job', 'job_id'),
        Index('ix_optimization_trials_score', 'score'),
    )
