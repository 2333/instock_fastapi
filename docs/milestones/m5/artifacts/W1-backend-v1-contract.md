# W1 Backend V1 Contract Freeze

Date: 2026-05-20

## Schema Contract

`parameter_optimization_jobs`

- `id`: integer primary key.
- `user_id`: integer, required. Owner boundary for every read/write API.
- `name`: optional string, max 120.
- `method`: required string. Allowed value: `random_search`.
- `status`: required string. Allowed values: `pending`, `running`, `completed`, `failed`, `cancelled`.
- `progress`: required integer, `0..100` by service contract.
- `base_params`: JSONB, required. The original Backtest config.
- `parameter_space`: JSONB, required. Up to 8 parameters.
- `objective_metric`: required string. Allowed values: `sharpe_ratio`, `total_return`, `max_drawdown`.
- `objective_direction`: required string. Allowed values: `maximize`, `minimize`.
- `trial_count`: required integer, `1..50`.
- `completed_trials`, `failed_trials`: required integers.
- `random_seed`: optional integer.
- `best_trial_id`: optional integer.
- `best_parameters`, `best_metrics`: optional JSONB.
- `best_score`: optional float.
- `error_message`: optional text.
- `created_at`, `updated_at`, `started_at`, `completed_at`: timestamps.

Indexes:

- `ix_parameter_optimization_jobs_user_created(user_id, created_at)`
- `ix_parameter_optimization_jobs_status(status)`

`parameter_optimization_trials`

- `id`: integer primary key.
- `job_id`: required FK to `parameter_optimization_jobs.id`.
- `trial_index`: required integer, unique per job.
- `status`: required string. Allowed values match job status.
- `params`: JSONB, required. The sampled trial parameters.
- `metrics`: optional JSONB. Contains `sharpe_ratio`, `total_return`, `max_drawdown`.
- `score`: optional float. Normalized for comparison.
- `backtest_result`: optional JSONB. Stores bounded `summary`, `meta`, and `backtest_id`.
- `error_message`: optional text.
- `created_at`, `started_at`, `completed_at`: timestamps.

Indexes and constraints:

- `uq_parameter_optimization_trials_job_index(job_id, trial_index)`
- `ix_parameter_optimization_trials_job_id(job_id)`
- `ix_parameter_optimization_trials_status(status)`

## API Contract

- `POST /api/v1/optimization/jobs`
  - Query: `auto_start=true` by default. Use `false` for contract tests or manual staging setup.
  - Body: `name`, `base_params`, `parameter_space`, `method=random_search`, `objective_metric`, `objective_direction`, `trial_count`, `random_seed`.
  - Response: `201`, `ParameterOptimizationJobResponse`.
  - Validation failure: `422`.
- `GET /api/v1/optimization/jobs?limit=20`
  - Owner-scoped list, newest first.
- `GET /api/v1/optimization/jobs/{job_id}`
  - Owner-scoped detail.
  - Missing or non-owner job returns `404`.
- `DELETE /api/v1/optimization/jobs/{job_id}`
  - Cancels `pending` or `running`.
  - Terminal jobs return `409`.
- `GET /api/v1/optimization/jobs/{job_id}/trials`
  - Owner-scoped trial list ordered by `trial_index`.
- `GET /api/v1/optimization/jobs/{job_id}/best`
  - Returns best trial fields plus `backtest_params`, which is the original Backtest config merged with `best_parameters`.

## Parameter Space Contract

Allowed parameter specs:

- Choices shorthand: `"fast_ma": [3, 5, 8]`
- Choice object: `"fast_ma": {"type": "choice", "values": [3, 5, 8]}`
- Integer range: `"fast_ma": {"type": "int", "min": 3, "max": 8, "step": 1}`
- Float range: `"threshold": {"type": "float", "min": 0.1, "max": 0.9, "step": 0.1}`

Parameter application:

- `strategy_params.foo` writes `base_params["strategy_params"]["foo"]`.
- A key already present at top level of `base_params` overwrites that top-level field.
- Other keys write into `base_params["strategy_params"]`.

## Runtime Limits

- Maximum parameters per job: 8.
- Maximum trials per job: 50.
- v1 supports `random_search` only.
- v1 uses in-process `asyncio` task scheduling with a fresh DB session per optimization task.
- v1 does not attempt restart recovery after process death; persisted `pending` / `running` rows remain inspectable and can be cancelled or retried by a later enhancement.

## Smoke Path

1. Create a job with `auto_start=false` and a small finite parameter space.
2. Confirm the job is visible through list and detail APIs.
3. Run the focused service test path or start normally with `auto_start=true`.
4. Poll the detail endpoint until `status` is terminal.
5. Fetch trials and best.
6. Use `data.backtest_params` as the Backtest config for a normal `/api/v1/backtest` call.

## Rollback

- Remove `optimization_router` registration to close the API entry point.
- Run Alembic downgrade from `m5_parameter_optimization` to `m3_notification_legacy_type_nullable` to drop the two new tables.
- Existing Backtest models, APIs, and tables are not mutated by this slice.
