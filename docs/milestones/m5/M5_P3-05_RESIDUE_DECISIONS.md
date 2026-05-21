# M5 / P3-05 Residue Decisions

更新时间：2026-05-21

## `app/optimization/algorithms.py`

Decision：保留但隔离。

当前状态：

- 文件存在，但没有 router、service、task、model 或 tests 接入。
- `RandomSearchOptimizer` 和 `BayesianOptimizer` 可作为算法原型参考。
- 贝叶斯分支的接口和终止条件还不适合作为 runtime contract。

约束：

- 不在架构图或类图中作为当前 runtime 能力展示。
- 不在 `M5 v1` 中直接接线，除非先补 adapter contract 和 focused tests。
- 若 `M5 v1` 决定不复用该文件，应把可取的算法说明回填到设计文档后删除。

## 前端 optimization 残留

Decision：旧独立页面与旧 API 假设不恢复；`M5 v1` 只从 Backtest 页面接入新的 API contract。

当前状态：

- `Backtest.vue` 已接入 `M5 v1` 最小参数优化 UI。
- 当前没有独立 `Optimization.vue` 页面。
- `web/src/api/index.ts` 已有新的 `optimizationApi`，只对应 `M5 v1` 后端 contract。

约束：

- `M5` 前端实现不得直接恢复历史页面或旧 API 假设。
- 后续如果抽出独立页面，必须另开 alignment note，不得把它当作本轮 v1 的自然延伸。

## P3-05 旧设计文档

Decision：保留为设计资产，但去除错误当前态。

已修正方向：

- 移除“Celery/RQ 已存在”假设。
- 移除“optimizationApi 已存在 / 后端 API 已就绪”假设。
- 将贝叶斯优化降为可选增强。
- 将 `M5` 首轮锚定到现有 `BacktestService` 与 async task 模式。
