"""Parameter optimization service for M5 / P3-05."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import ParameterOptimizationJob, ParameterOptimizationTrial
from app.schemas.optimization_schema import ParameterOptimizationJobCreate
from app.services.backtest_service import BacktestService


class OptimizationNotFoundError(Exception):
    pass


class OptimizationConflictError(Exception):
    pass


class OptimizationValidationError(ValueError):
    pass


class OptimizationService:
    MAX_PARAMETERS = 8
    MAX_TRIALS = 50
    SUPPORTED_METRICS = {"sharpe_ratio", "total_return", "max_drawdown"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(
        self,
        *,
        user_id: int,
        payload: ParameterOptimizationJobCreate,
    ) -> ParameterOptimizationJob:
        self._validate_parameter_space(payload.parameter_space, payload.trial_count)
        job = ParameterOptimizationJob(
            user_id=user_id,
            name=payload.name,
            method=payload.method,
            status="pending",
            progress=0,
            base_params=payload.base_params,
            parameter_space=payload.parameter_space,
            objective_metric=payload.objective_metric,
            objective_direction=payload.objective_direction or "maximize",
            trial_count=payload.trial_count,
            random_seed=payload.random_seed,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def list_jobs(self, *, user_id: int, limit: int = 20) -> list[ParameterOptimizationJob]:
        result = await self.db.execute(
            select(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.user_id == user_id)
            .order_by(ParameterOptimizationJob.created_at.desc(), ParameterOptimizationJob.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_job(self, *, job_id: int, user_id: int) -> ParameterOptimizationJob:
        job = await self._get_job_for_user(job_id=job_id, user_id=user_id)
        if job is None:
            raise OptimizationNotFoundError("optimization job not found")
        return job

    async def cancel_job(self, *, job_id: int, user_id: int) -> ParameterOptimizationJob:
        job = await self.get_job(job_id=job_id, user_id=user_id)
        if job.status in {"completed", "failed", "cancelled"}:
            raise OptimizationConflictError("optimization job is already terminal")
        now = datetime.utcnow()
        job.status = "cancelled"
        job.progress = 100
        job.completed_at = now
        await self._cancel_pending_trials(job_id=job.id, completed_at=now)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def list_trials(
        self,
        *,
        job_id: int,
        user_id: int,
    ) -> list[ParameterOptimizationTrial]:
        await self.get_job(job_id=job_id, user_id=user_id)
        result = await self.db.execute(
            select(ParameterOptimizationTrial)
            .where(ParameterOptimizationTrial.job_id == job_id)
            .order_by(ParameterOptimizationTrial.trial_index.asc())
        )
        return list(result.scalars().all())

    async def get_best(self, *, job_id: int, user_id: int) -> dict[str, Any]:
        job = await self.get_job(job_id=job_id, user_id=user_id)
        return self._best_payload(job)

    async def run_job(self, *, job_id: int) -> ParameterOptimizationJob:
        job = await self.db.get(ParameterOptimizationJob, job_id)
        if job is None:
            raise OptimizationNotFoundError("optimization job not found")
        if job.status == "cancelled":
            return job
        if job.status not in {"pending", "running"}:
            raise OptimizationConflictError("optimization job is already terminal")

        now = datetime.utcnow()
        job.status = "running"
        job.started_at = job.started_at or now
        job.progress = max(job.progress or 0, 1)
        await self.db.commit()
        await self.db.refresh(job)

        try:
            self._validate_parameter_space(job.parameter_space, job.trial_count)
            if job.objective_metric not in self.SUPPORTED_METRICS:
                raise OptimizationValidationError("unsupported objective_metric")
            candidates = self._generate_candidates(
                job.parameter_space,
                trial_count=job.trial_count,
                random_seed=job.random_seed,
            )
        except Exception as exc:
            await self._mark_job_failed(job, str(exc))
            return job

        successful_trials = 0
        failed_trials = 0
        best_score = job.best_score
        best_trial_id = job.best_trial_id
        best_parameters = job.best_parameters
        best_metrics = job.best_metrics

        for index, candidate in enumerate(candidates, start=1):
            await self.db.refresh(job)
            if job.status == "cancelled":
                await self._cancel_remaining_trials(
                    job_id=job.id,
                    from_index=index,
                    candidates=candidates,
                )
                return job

            trial = ParameterOptimizationTrial(
                job_id=job.id,
                trial_index=index,
                status="running",
                params=candidate,
                started_at=datetime.utcnow(),
            )
            self.db.add(trial)
            await self.db.commit()
            await self.db.refresh(trial)

            try:
                backtest_params = self._build_backtest_params(job.base_params, candidate)
                result = await BacktestService(self.db).run_backtest(backtest_params, user_id=None)
                metrics = self._extract_metrics(result)
                score = self._score_metrics(
                    metrics,
                    metric=job.objective_metric,
                    direction=job.objective_direction,
                )
            except Exception as exc:
                trial_status = "failed"
                trial_error = str(exc)
                trial_metrics = None
                trial_score = None
                trial_backtest_result = None
            else:
                trial_status = "completed"
                trial_error = None
                trial_metrics = metrics
                trial_score = score
                trial_backtest_result = {
                    "summary": result.get("summary") or {},
                    "meta": result.get("meta") or {},
                    "backtest_id": result.get("backtest_id"),
                }

            await self.db.refresh(job)
            if job.status == "cancelled":
                trial.status = "cancelled"
                trial.error_message = "job_cancelled"
                trial.completed_at = datetime.utcnow()
                await self._cancel_remaining_trials(
                    job_id=job.id,
                    from_index=index + 1,
                    candidates=candidates,
                )
                await self.db.commit()
                return job

            if trial_status == "failed":
                failed_trials += 1
                trial.status = "failed"
                trial.error_message = trial_error
                trial.completed_at = datetime.utcnow()
            else:
                successful_trials += 1
                trial.status = "completed"
                trial.metrics = trial_metrics
                trial.score = trial_score
                trial.backtest_result = trial_backtest_result
                trial.completed_at = datetime.utcnow()
                if best_score is None or trial_score > best_score:
                    best_score = score
                    best_trial_id = trial.id
                    best_parameters = candidate
                    best_metrics = metrics

            job.completed_trials = successful_trials
            job.failed_trials = failed_trials
            job.best_score = best_score
            job.best_trial_id = best_trial_id
            job.best_parameters = best_parameters
            job.best_metrics = best_metrics
            job.progress = min(99, int(((successful_trials + failed_trials) / job.trial_count) * 100))
            await self.db.commit()

        await self.db.refresh(job)
        if job.status == "cancelled":
            return job

        job.completed_at = datetime.utcnow()
        job.progress = 100
        if successful_trials:
            job.status = "completed"
            job.error_message = None
        else:
            job.status = "failed"
            job.error_message = "all optimization trials failed"
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _get_job_for_user(
        self,
        *,
        job_id: int,
        user_id: int,
    ) -> ParameterOptimizationJob | None:
        result = await self.db.execute(
            select(ParameterOptimizationJob).where(
                ParameterOptimizationJob.id == job_id,
                ParameterOptimizationJob.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _mark_job_failed(self, job: ParameterOptimizationJob, message: str) -> None:
        job.status = "failed"
        job.progress = 100
        job.error_message = message
        job.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(job)

    async def _cancel_pending_trials(self, *, job_id: int, completed_at: datetime) -> None:
        result = await self.db.execute(
            select(ParameterOptimizationTrial).where(
                ParameterOptimizationTrial.job_id == job_id,
                ParameterOptimizationTrial.status.in_(("pending", "running")),
            )
        )
        for trial in result.scalars():
            trial.status = "cancelled"
            trial.completed_at = completed_at

    async def _cancel_remaining_trials(
        self,
        *,
        job_id: int,
        from_index: int,
        candidates: list[dict[str, Any]],
    ) -> None:
        now = datetime.utcnow()
        for index, candidate in enumerate(candidates[from_index - 1 :], start=from_index):
            self.db.add(
                ParameterOptimizationTrial(
                    job_id=job_id,
                    trial_index=index,
                    status="cancelled",
                    params=candidate,
                    completed_at=now,
                )
            )
        await self.db.commit()

    def _best_payload(self, job: ParameterOptimizationJob) -> dict[str, Any]:
        backtest_params = None
        if job.best_parameters:
            backtest_params = self._build_backtest_params(job.base_params, job.best_parameters)
        return {
            "job_id": job.id,
            "status": job.status,
            "best_trial_id": job.best_trial_id,
            "best_parameters": job.best_parameters,
            "best_metrics": job.best_metrics,
            "best_score": job.best_score,
            "backtest_params": backtest_params,
        }

    def _validate_parameter_space(
        self,
        parameter_space: dict[str, Any],
        trial_count: int,
    ) -> None:
        if not parameter_space:
            raise OptimizationValidationError("parameter_space is required")
        if len(parameter_space) > self.MAX_PARAMETERS:
            raise OptimizationValidationError("parameter_space exceeds maximum size")
        if trial_count < 1 or trial_count > self.MAX_TRIALS:
            raise OptimizationValidationError("trial_count must be between 1 and 50")

        finite_combinations = 1
        all_finite = True
        for name, spec in parameter_space.items():
            if not isinstance(name, str) or not name.strip():
                raise OptimizationValidationError("parameter names must be non-empty strings")
            count = self._validate_parameter_spec(name, spec)
            if count is None:
                all_finite = False
            else:
                finite_combinations *= count
        if all_finite and finite_combinations < trial_count:
            raise OptimizationValidationError("trial_count exceeds available parameter combinations")

    def _validate_parameter_spec(self, name: str, spec: Any) -> int | None:
        if isinstance(spec, list):
            if not spec:
                raise OptimizationValidationError(f"{name} choices cannot be empty")
            return len(spec)
        if not isinstance(spec, dict):
            raise OptimizationValidationError(f"{name} must be a choices list or range spec")

        spec_type = spec.get("type")
        if spec_type == "choice":
            values = spec.get("values")
            if not isinstance(values, list) or not values:
                raise OptimizationValidationError(f"{name}.values must be a non-empty list")
            return len(values)
        if spec_type not in {"int", "float"}:
            raise OptimizationValidationError(f"{name}.type must be int, float, or choice")
        if "min" not in spec or "max" not in spec:
            raise OptimizationValidationError(f"{name} range requires min and max")
        min_value = spec["min"]
        max_value = spec["max"]
        if not isinstance(min_value, int | float) or not isinstance(max_value, int | float):
            raise OptimizationValidationError(f"{name} range bounds must be numeric")
        if min_value > max_value:
            raise OptimizationValidationError(f"{name}.min must be <= max")
        step = spec.get("step")
        if step is None:
            return (int(max_value) - int(min_value) + 1) if spec_type == "int" else None
        if spec_type == "int" and not isinstance(step, int):
            raise OptimizationValidationError(f"{name}.step must be an integer for int ranges")
        if not isinstance(step, int | float) or step <= 0:
            raise OptimizationValidationError(f"{name}.step must be positive")
        return int((float(max_value) - float(min_value)) / float(step)) + 1

    def _generate_candidates(
        self,
        parameter_space: dict[str, Any],
        *,
        trial_count: int,
        random_seed: int | None,
    ) -> list[dict[str, Any]]:
        rng = random.Random(random_seed)
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[tuple[str, Any], ...]] = set()
        max_attempts = trial_count * 20
        attempts = 0
        while len(candidates) < trial_count and attempts < max_attempts:
            attempts += 1
            candidate = {
                name: self._sample_parameter(spec, rng=rng)
                for name, spec in parameter_space.items()
            }
            key = tuple(sorted(candidate.items()))
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
        if len(candidates) < trial_count:
            raise OptimizationValidationError("unable to generate enough unique trials")
        return candidates

    def _sample_parameter(self, spec: Any, *, rng: random.Random) -> Any:
        if isinstance(spec, list):
            return rng.choice(spec)
        if spec.get("type") == "choice":
            return rng.choice(spec["values"])
        min_value = spec["min"]
        max_value = spec["max"]
        step = spec.get("step")
        if spec.get("type") == "int":
            if step is None:
                return rng.randint(int(min_value), int(max_value))
            steps = int((int(max_value) - int(min_value)) / int(step))
            return int(min_value) + rng.randint(0, steps) * int(step)
        if step is None:
            return round(rng.uniform(float(min_value), float(max_value)), 6)
        steps = int((float(max_value) - float(min_value)) / float(step))
        return round(float(min_value) + rng.randint(0, steps) * float(step), 6)

    def _build_backtest_params(
        self,
        base_params: dict[str, Any],
        trial_params: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(base_params)
        strategy_params = dict(params.get("strategy_params") or {})
        for key, value in trial_params.items():
            if key.startswith("strategy_params."):
                strategy_params[key.split(".", 1)[1]] = value
            elif key in params and key != "strategy_params":
                params[key] = value
            else:
                strategy_params[key] = value
        params["strategy_params"] = strategy_params
        return params

    def _extract_metrics(self, result: dict[str, Any]) -> dict[str, float]:
        if result.get("status") != "completed":
            raise OptimizationValidationError(str(result.get("error") or "backtest failed"))
        summary = result.get("summary") or {}
        metrics: dict[str, float] = {}
        for metric in self.SUPPORTED_METRICS:
            value = summary.get(metric)
            if value is None:
                raise OptimizationValidationError(f"backtest summary missing {metric}")
            metrics[metric] = float(value)
        return metrics

    def _score_metrics(
        self,
        metrics: dict[str, float],
        *,
        metric: str,
        direction: str,
    ) -> float:
        raw_value = metrics[metric]
        value = abs(raw_value) if metric == "max_drawdown" else raw_value
        return -value if direction == "minimize" else value
