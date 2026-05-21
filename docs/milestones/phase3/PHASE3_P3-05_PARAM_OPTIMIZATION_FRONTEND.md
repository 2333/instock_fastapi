# Phase 3 设计资产：P3-05 参数优化前端输入

更新时间：2026-05-21

> 本文档是 `M5` 前端实现的设计输入，不是当前执行计划。执行拆分、并行任务和 reviewer gate 以 [`../m5/M5_P3-05_KICKOFF_PLAN.md`](../m5/M5_P3-05_KICKOFF_PLAN.md) 为准。

## 当前决策

- `M5 v1` 后端 API contract 已冻结，前端通过 `web/src/api/index.ts` 中的 `optimizationApi` 接入。
- 当前没有独立 `Optimization.vue` 页面；历史页面曾在 rebaseline 中移除，`M5 v1` 不恢复旧入口。
- 首轮 UI 应偏工作台/工具形态，不做营销式页面。
- 首轮进度更新使用轮询即可，不需要 WebSocket。

## 首轮前端范围

### 必须

- 创建优化任务表单：复用当前 Backtest 配置，选择参数空间、目标指标和 trial 数。
- 任务状态：状态、进度、当前 best score。
- Trial 摘要：展示最近 trial 状态和 score。
- 最优参数应用：把 best 参数填回 Backtest 配置。
- 错误和取消状态可见。

### 可选增强

- 散点图。
- 平行坐标图。
- Dashboard 最近优化任务卡片。
- 独立 `/optimization` 页面。

## 推荐入口

首轮推荐从 `Backtest.vue` 接入：

- 用户已经在回测上下文内配置策略、股票和日期。
- 最优参数回填路径最短。
- 避免过早恢复历史 `/optimization` 页面造成范围膨胀。

如果后端 API 和产品体验稳定，再把 Optimization 拆成独立页面。

## API 草案

```text
POST   /api/v1/optimization/jobs
GET    /api/v1/optimization/jobs
GET    /api/v1/optimization/jobs/{job_id}
DELETE /api/v1/optimization/jobs/{job_id}
GET    /api/v1/optimization/jobs/{job_id}/trials
GET    /api/v1/optimization/jobs/{job_id}/best
```

## 验收

- `npm run typecheck` 通过。
- `npm run build` 通过。
- 表单能创建任务。
- 列表和详情能正确展示 running/completed/failed/cancelled。
- best 参数可回填到 Backtest 表单。
- API loading/error/empty state 完整。
