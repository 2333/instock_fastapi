# M5 / P3-05 参数优化 Kickoff Plan

更新时间：2026-05-20

## 目标

启动 `M5 / P3-05` 参数优化服务，在不引入不必要新基础设施的前提下，交付一个可验收、可回滚、可扩展的最小闭环：

```text
Backtest 配置
  -> 创建 Optimization Job
  -> 执行有限 Trial
  -> 存储 Trial 指标和状态
  -> 计算 Best Parameters
  -> 回填到 Backtest 配置
```

## 非目标

- 不在 kickoff 阶段实现功能代码。
- `M5 v1` 不默认引入 Celery/RQ 或新的队列系统。
- 不恢复历史 `Optimization.vue` 或旧 `optimizationApi`，除非前后端 contract 已重新冻结。
- 不把贝叶斯优化作为 v1 硬验收，除非其接口、终止条件和测试在实现前补齐。
- 不把 M6 数据洞察或 M7 推荐带入本轮。

## Gate 0：启动前冻结项

`M5` 实现前必须冻结：

- Execution governance：每个 work stream 使用 `planner alignment -> implementation -> reviewer gate`，且 reviewer 可因无 note、超 note 或 evidence mismatch 直接 `NO-GO`。
- Runtime 决策：首轮复用 `BacktestService` 与当前 async task 模式。
- Schema contract：`parameter_optimization_jobs`、`parameter_optimization_trials` 的字段、索引、状态机和回滚策略。
- API contract：创建、列表、详情、取消、trial 列表、best 参数。
- Trial 限制：参数数量、trial 数量、单用户并发、任务取消语义。
- Residue disposition：`app/optimization/algorithms.py` 与历史前端入口假设只作为未接入资产，不代表现行 runtime。
- 手工 smoke：至少一条从创建 job 到 best 参数回填的可复现路径。

Gate 0 未通过，不进入并行实现。

## Planner Alignment Note

每个 work stream 或新增 / 扩 scope 的变更项，在 implementation 前必须先由 planner 明确认可一份 alignment note。

最小字段：

- Scope：本 note 覆盖的行为、文档或代码边界。
- Write set：允许修改的文件 / 模块；跨 write set 必须重新对齐。
- Dependencies：前置 contract、其他 work stream、环境或数据依赖。
- Non-goals：明确不做的能力，防止顺手扩散。
- Acceptance：完成后必须满足的检查项。
- Rollback boundary：出问题时如何回退或隔离，不影响既有主线。
- Evidence plan：预期命令、smoke、截图、artifact 或 reviewer 证据。
- Owner / reviewer / blocking questions：可选但推荐写明。

粒度规则：

- 一条 note 只覆盖一个可审阅的 cohesive write set。
- 如果 write set 扩大、依赖变化、acceptance 变化，必须新开或修订 note，并显式标版本。
- 不允许用一个宽泛 note 覆盖整轮 `M5` 全部实现。
- 实现偏离已批准 note 时，必须停止当前 slice 并重新 alignment。

## 并行任务拆分

### WS-1 Schema / Model

Owner：backend worker

输出：

- `ParameterOptimizationJob` / `ParameterOptimizationTrial` ORM 模型。
- Alembic migration。
- 状态机约束和索引。
- schema-contract release gate 说明。

验收：

- `alembic upgrade head` 可执行。
- migration 可独立回滚。
- 不改变现有 backtest 表语义。

### WS-2 Service / Engine

Owner：backend worker

输出：

- 参数空间校验。
- `random_search` optimizer adapter。
- objective metric 提取：`sharpe_ratio`、`total_return`、`max_drawdown`。
- job/trial 进度与 best score 更新。

验收：

- 有 focused unit tests。
- 单个 trial 失败不拖垮整个 job。
- `app/optimization/algorithms.py` 若被复用，必须补测试和接口收口；否则保留隔离。

### WS-3 API / Task Runtime

Owner：backend worker

输出：

- `optimization_router.py`。
- `optimization_task.py` 或等价 async runner。
- 当前用户权限隔离。
- 取消语义。

验收：

- 非 owner 不能访问 job。
- running job 可取消。
- API contract 与前端 mock 一致。

### WS-4 Frontend

Owner：frontend worker

输出：

- Backtest 参数优化入口或独立页面的最小实现。
- 创建 job 表单。
- job 列表和详情。
- best 参数回填到 Backtest。
- loading / error / empty / cancelled 状态。

验收：

- `npm run typecheck` 通过。
- `npm run build` 通过。
- 手工路径可跑通。

### WS-5 Tests / Ops / Review

Owner：controller + reviewer

输出：

- focused backend tests。
- frontend typecheck/build。
- API smoke。
- release/staging 验证脚本或手工步骤。
- reviewer artifact。

验收：

- 所有 schema-changing 变更走 `schema_contract` gate。
- 文档、API、代码状态一致。
- M5 可以独立验收、独立回滚。

## 建议实施顺序

1. Gate 0：先冻结本执行治理规则、runtime 决策、API/schema/status/smoke 边界，并通过 planner + reviewer。
2. 每个 WS 先形成独立 planner alignment note；只有 note 被认可且依赖满足后，才允许 implementation。
3. WS-1、WS-4、WS-5 可在各自 alignment note 完成后并行。
4. WS-2 必须与 WS-1 共用同一 schema/API contract；如果 contract 变化，两个 WS 都要更新 alignment note。
5. WS-3 在 WS-1/WS-2 合同稳定后接入。
6. 每个 implementation slice 完成后进入 reviewer gate，reviewer 结论必须是 `approved` / `changes requested` / `no-go` 之一。

## Stop Condition

本启动前置工作在以下条件满足时停止：

- 文档 active route 已统一到 `M5 / P3-05`。
- `docs/milestones/m5/` 执行包完整。
- P3-05 设计文档不再包含错误的 Celery/RQ/optimizationApi 已存在假设。
- optimization 代码残片有明确 disposition。
- M5 执行治理规则已写入 README、kickoff、review checklist 与 artifacts 模板。
- reviewer 确认 `M5` 可以启动。
