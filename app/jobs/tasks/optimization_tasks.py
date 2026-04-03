import asyncio
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.optimization_models import ParameterOptimizationJob, ParameterOptimizationTrial
from app.optimization.algorithms import create_optimizer, Trial
from app.services.optimization_service import OptimizationService

logger = logging.getLogger(__name__)


class OptimizationExecutor:
    """优化任务执行器"""

    def __init__(self, job_id: int):
        self.job_id = job_id
        self.service: Optional[OptimizationService] = None
        self.job: Optional[ParameterOptimizationJob] = None
        self.optimizer = None
        self._stop_requested = False

    async def run(self):
        """执行优化任务主循环"""
        async with async_session_factory() as session:
            self.service = OptimizationService(session)

            # 加载任务
            self.job = await self.service.get_job(self.job_id)
            if not self.job:
                logger.error("Optimization job %d not found", self.job_id)
                return

            if self.job.status in ("completed", "failed", "cancelled"):
                logger.info("Job %d already %s, skipping", self.job_id, self.job.status)
                return

            # 标记为运行中
            await self.service.mark_job_running(self.job_id)

            try:
                await self._execute_optimization()
            except asyncio.CancelledError:
                logger.info("Job %d cancelled", self.job_id)
                await self.service.mark_job_failed(self.job_id, "Cancelled by user")
            except Exception as e:
                logger.exception("Job %d failed with exception", self.job_id)
                await self.service.mark_job_failed(self.job_id, str(e))

    async def _execute_optimization(self):
        """执行优化循环"""
        assert self.job and self.service

        # 构建参数空间
        param_space = self.job.parameter_space

        # 创建优化器
        self.optimizer = create_optimizer(
            method=self.job.optimization_method,
            param_space=param_space,
            objective=self.job.objective_metric,
            n_trials=self.job.total_trials,
        )

        # 并发控制
        semaphore = asyncio.Semaphore(self.job.max_parallel)

        # 试验生成器
        async def trial_generator():
            while not self.optimizer.is_done() and not self._stop_requested:
                suggestions = await self.optimizer.suggest(n=1)
                for params in suggestions:
                    yield params

        # 执行试验
        async for params in trial_generator():
            trial = await self.service.create_trial(self.job_id, params)

            async with semaphore:
                try:
                    score, metrics, backtest_id = await self._run_backtest(params)
                    await self.service.update_trial_result(
                        trial_id=trial.id,
                        score=score,
                        metrics=metrics,
                        backtest_result_id=backtest_id,
                    )
                    self.optimizer.record_trial(params, score, backtest_result_id=backtest_id)
                except Exception as e:
                    logger.warning("Trial failed: %s", e)
                    await self.service.update_trial_result(trial_id=trial.id, score=None, error=str(e))
                    self.optimizer.record_trial(params, None, error=str(e))

            # 更新进度
            completed = len(self.optimizer.trials)
            best_score = self.optimizer.get_best_score()
            best_params = self.optimizer.get_best_parameters()
            await self.service.update_job_progress(
                self.job_id,
                completed_trials=completed,
                best_score=best_score,
                best_params=best_params,
            )

        # 任务完成
        best_params = self.optimizer.get_best_parameters()
        best_score = self.optimizer.get_best_score()

        if best_params and best_score is not None:
            # 用最优参数跑一次回测，获取 backtest_result_id
            _, _, best_backtest_id = await self._run_backtest(best_params, record_result=True)
            await self.service.mark_job_completed(
                self.job_id,
                best_parameters=best_params,
                best_score=best_score,
                best_backtest_result_id=best_backtest_id,
            )
            logger.info("Optimization job %d completed. Best score: %f", self.job_id, best_score)
        else:
            await self.service.mark_job_failed(self.job_id, "No valid trials completed")

    async def _run_backtest(
        self,
        params: Dict[str, Any],
        record_result: bool = False,
    ) -> tuple[Optional[float], Dict[str, Any], Optional[int]]:
        """
        执行单次回测并返回目标指标
        
        返回: (score, metrics, backtest_result_id)
        """
        assert self.job

        # 构建回测请求
        backtest_payload = {
            "strategy": self.job.strategy_type,
            "strategy_params": params,
            "start_date": self.job.parameter_space.get("start_date", "2024-01-01"),
            "end_date": self.job.parameter_space.get("end_date", "2025-01-01"),
            "initial_capital": self.job.parameter_space.get("initial_capital", 100000),
            "stock_code": self.job.parameter_space.get("stock_code", "600519"),
        }

        # 调用回测 API（需要实现 HTTP 调用或直接调用服务层）
        # 这里简化：模拟回测结果
        # 实际应调用 backtestApi.runBacktest()
        await asyncio.sleep(0.5)  # 模拟耗时

        # 模拟指标计算
        # 实际应从回测结果提取
        import random
        base_score = random.uniform(0.5, 2.5)  # 模拟夏普比率

        metrics = {
            "total_return": base_score * 100,
            "sharpe_ratio": base_score,
            "max_drawdown": random.uniform(5, 20),
            "win_rate": random.uniform(0.4, 0.7),
            "trade_count": random.randint(10, 50),
        }

        score = metrics[self.job.objective_metric] if self.job.objective_metric in metrics else base_score

        backtest_result_id = None
        if record_result:
            # 保存回测结果到数据库（待实现）
            backtest_result_id = 1  # 占位

        return score, metrics, backtest_result_id

    def stop(self):
        """请求停止优化"""
        self._stop_requested = True


async def run_optimization_job(job_id: int):
    """Celery/APScheduler 任务入口"""
    executor = OptimizationExecutor(job_id)
    await executor.run()
