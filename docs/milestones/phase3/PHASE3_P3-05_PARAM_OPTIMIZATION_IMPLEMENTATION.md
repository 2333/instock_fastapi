# Phase 3 设计资产：P3-05 参数优化后端实现输入

更新时间：2026-05-20

> 本文档是 `M5` 后端实现的设计输入，不是当前执行计划。执行拆分、并行任务和 reviewer gate 以 [`../m5/M5_P3-05_KICKOFF_PLAN.md`](../m5/M5_P3-05_KICKOFF_PLAN.md) 为准。

## 当前决策

- 首轮不引入新的任务队列系统。
- 首轮复用现有 `BacktestService` 和当前 async task 模式。
- `random_search` 是 v1 必须支持的优化方法。
- 贝叶斯优化保留为可选增强；只有补齐接口语义、终止条件和测试后才能进入 runtime。
- `app/optimization/algorithms.py` 是 isolated prototype，不直接代表已实现服务。

## 后端最小范围

### 新增

- `app/models/optimization_models.py`
- `app/schemas/optimization_schema.py`
- `app/services/optimization_service.py`
- `app/jobs/tasks/optimization_task.py`
- `app/api/routers/optimization_router.py`
- Alembic migration：`parameter_optimization_jobs`、`parameter_optimization_trials`
- focused tests：算法采样、任务状态流转、API 权限、取消语义、best score 计算

### 修改

- `app/main.py`：注册 optimization router。
- `app/models/__init__.py`：导出新模型。
- `app/api/routers/__init__.py`：如需要，导出新 router。
- `docs/architecture/system_architecture.md` 与 `docs/design/class_diagram.md`：只在 runtime 入口实现后再加入 optimization，不在 kickoff 前预写未来态。

## 服务边界

```text
OptimizationService
  create_job()
  list_jobs()
  get_job()
  cancel_job()
  list_trials()
  get_best()
  run_job()
```

`run_job()` 应该：

1. 标记 job 为 `running`。
2. 校验参数空间和 trial 上限。
3. 生成参数组合。
4. 对每个 trial 调用 `BacktestService.run_backtest()` 或后续冻结的等价评估接口。
5. 写入 trial 的参数、指标、score、状态和错误。
6. 持续更新 `completed_trials`、`best_parameters`、`best_score`。
7. 在取消、失败和完成时写入清晰状态。

## API 草案

```text
POST   /api/v1/optimization/jobs
GET    /api/v1/optimization/jobs
GET    /api/v1/optimization/jobs/{job_id}
DELETE /api/v1/optimization/jobs/{job_id}
GET    /api/v1/optimization/jobs/{job_id}/trials
GET    /api/v1/optimization/jobs/{job_id}/best
```

## 状态机

```text
pending -> running -> completed
pending -> cancelled
running -> cancelled
running -> failed
```

约束：

- 已完成 job 不允许取消。
- 取消 job 后，未开始 trial 标记为 `cancelled`。
- 单个 trial 失败不必导致整个 job 失败；只有所有 trial 都失败或任务级错误才标记 job failed。

## 回滚边界

- Schema-changing release 必须走 `schema_contract` gate。
- 首轮新增表应可独立回滚，不改变既有 backtest 表语义。
- Optimization router 可通过不注册路由回滚入口；数据表保留不影响现有功能。

## 后端验收

- Alembic upgrade 到 head 成功。
- 创建 job 后能看到 progress 变化。
- 至少一个 job 完成后产生 trial 和 best 参数。
- 取消 running job 后状态明确。
- 非 owner 访问返回 404 或 403。
- focused tests 通过，且不破坏现有 backtest tests。
