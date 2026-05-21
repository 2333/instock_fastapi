# Phase 3 设计资产：P3-05 参数优化服务

更新时间：2026-05-20

> 当前执行入口不是本文档，而是 [`docs/milestones/m5/README.md`](../m5/README.md)。本文档只保留产品与技术设计输入；任务拆分、scope freeze、reviewer gate 和启动裁决以 `m5/` 执行包为准。

## 目标

为回测策略自动寻找更优参数组合，减少用户反复手工调参的成本，并把“为什么这个参数更好”用可解释的 trial 结果呈现出来。

## 当前代码现实

- 已具备：认证、回测、异步回测任务、策略模板、回测历史、ECharts 前端基础。
- 已具备：`app/optimization/algorithms.py` 中存在随机搜索和贝叶斯优化算法原型。
- 未具备：参数优化 ORM 模型、迁移、服务、API、前端页面和运行时入口。
- 重要约束：当前默认运行形态没有独立任务队列；`M5` 首轮应复用现有 `BacktestService` 与当前 async task 模式，不默认引入新队列系统。
- 重要约束：`app/optimization/algorithms.py` 当前是 isolated prototype，不视为 runtime-ready 能力；是否复用由 `M5` kickoff gate 决定。

## M5 首轮最小闭环

```text
用户选择策略和参数空间
  -> 创建 optimization job
  -> 生成有限 trial 参数组合
  -> 调用 BacktestService 评估每组参数
  -> 存储 trial 参数、指标、状态和错误
  -> 更新 job progress、best_parameters、best_score
  -> 前端展示进度、结果对比和最优参数
  -> 用户一键把最优参数应用到 Backtest 配置
```

首轮必须避免把能力做散：只要能完成上面的闭环，就可以验收 `M5 v1`。贝叶斯优化、滚动稳健性、多图表和通知可以作为后续增强，但不能阻塞 v1。

## 推荐数据模型

### `parameter_optimization_jobs`

| 字段 | 说明 |
| --- | --- |
| `id` | 主键 |
| `user_id` | 任务所属用户 |
| `strategy_type` | 策略类型，例如 `ma_crossover`、`rsi_oversold` |
| `backtest_config` | 股票、时间范围、初始资金等回测配置 |
| `parameter_space` | 参数边界和步长 |
| `optimization_method` | 首轮默认 `random` |
| `objective_metric` | 默认 `sharpe_ratio`，可选 `total_return`、`max_drawdown` |
| `total_trials` / `completed_trials` | 进度 |
| `status` | `pending` / `running` / `completed` / `failed` / `cancelled` |
| `best_parameters` / `best_score` | 当前最优结果 |
| `error_message` | 失败原因 |
| `created_at` / `started_at` / `completed_at` | 生命周期时间 |

### `parameter_optimization_trials`

| 字段 | 说明 |
| --- | --- |
| `id` | 主键 |
| `job_id` | 关联 job |
| `trial_index` | 试验序号 |
| `parameters` | 本次参数 |
| `metrics` | 回测指标快照 |
| `score` | objective 计算后的分数 |
| `backtest_result_id` | 可选关联回测结果 |
| `status` | `pending` / `running` / `completed` / `failed` / `cancelled` |
| `error_message` | 单次试验失败原因 |
| `created_at` / `started_at` / `completed_at` | 生命周期时间 |

## API 草案

```text
POST   /api/v1/optimization/jobs
GET    /api/v1/optimization/jobs
GET    /api/v1/optimization/jobs/{job_id}
DELETE /api/v1/optimization/jobs/{job_id}
GET    /api/v1/optimization/jobs/{job_id}/trials
GET    /api/v1/optimization/jobs/{job_id}/best
```

约束：

- 所有接口必须带认证，且只能访问当前用户自己的 job。
- `DELETE` 首轮语义为取消任务，不物理删除历史记录。
- 任务执行模型必须在 `M5` kickoff 中冻结；首轮默认复用现有 async task 模式。

## 前端设计输入

- Backtest 页面或独立 Optimization 页面都可以承接，但首轮必须能从 Backtest 配置进入并回填最优参数。
- 结果展示先做“任务列表 + 详情 + trial 表 + best 参数卡片”；散点图和平行坐标图可作为增强。
- 页面轮询进度即可，不需要先引入 WebSocket。

## 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 参数空间过大导致计算失控 | 限制 `total_trials`、参数数量、并发数和单用户运行任务数 |
| 结果过拟合误导用户 | 首轮至少展示样本数量、目标指标和风险提示；滚动稳健性作为后续增强 |
| async task 进程重启后任务丢失 | 首轮必须把 job/trial 状态持久化；任务恢复策略在 kickoff 中明确是否纳入 v1 |
| 旧算法原型误用 | 在 `app/optimization/README.md` 和 `M5_P3-05_RESIDUE_DECISIONS.md` 中标注 isolated prototype |

## 验收方向

- 创建、查询、取消 job。
- trial 结果完整存储。
- progress 和 best 参数可查询。
- 至少支持 `random` 方法完成有限 trial。
- 可把 best 参数应用到现有回测配置。
- 后端 focused tests、前端 typecheck/build、本地自动化 API smoke 通过；live browser / staging 手工 smoke 属于 release activity。
