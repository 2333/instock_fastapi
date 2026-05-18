# M2 Kickoff Plan

> Status: acceptance ready
> Milestone: `M2 / P3-01 用户行为埋点`
> Last updated: 2026-04-20
> Controller: Codex

## 目标

交付首波最小可用行为事件采集闭环，为后续 `M6` 报告和 `M7` 推荐提供稳定输入，同时保持主流程可用、结构可回滚、验收可复现。

## 首波范围

- 后端新增 `user_events` 持久化模型与 Alembic migration
- 新增 `POST /api/v1/events/track`
- 前端新增 `useAnalytics` composable
- 接入 5 个核心页面:
  - `Dashboard`
  - `Selection`
  - `Backtest`
  - `StockDetail`
  - `Attention`
- 首波 6 类事件:
  - `page_view`
  - `dashboard_card_click`
  - `filter_run`
  - `backtest_run`
  - `pattern_view`
  - `attention_action`

## 非目标

- 不在本轮引入访客 / session 级事件
- 不做消息队列、异步消费、事件总线
- 不接收任意自由结构的埋点 payload
- 不把 `M1` follow-up 重新抬回 blocker
- 不提前实现 `10+` 事件类型扩展、归档、分区策略

## 阶段推进

| Phase | 目标 | 输入 | 输出 | Go / No-Go |
|------|------|------|------|------------|
| `P0` 契约冻结 | 冻结事件白名单、隐私边界、失败语义与验收口径 | `EXECUTION_PLAN`、`P3-01` 草案、现有页面接点 | `M2_EVENT_CONTRACT.md`、tracker、返工门禁 | 白名单与边界冻结前，不允许 worker 开始编码 |
| `P1` 后端闭环 | 交付表结构、迁移、track API、限流、focused tests | `P0` 契约 | `user_events`、migration、router/service、后端测试 | migration / focused tests 任一不稳即 no-go |
| `P2` 前端接入 | 交付 composable 与 5 页面首波事件发射 | `P1` API 与契约冻结 | `useAnalytics`、页面接线、API client、前端构建通过 | `typecheck` / `build` 失败即 no-go |
| `P3` 审核与验收 | 形成 reviewer 结论、SQL 样本、手工链路、回滚边界 | `P1` + `P2` | review 记录、验收文档、阶段汇报 | reviewer 未给 `go` 则返工，不进入 M2 可验收结论 |

## 分工

| Workstream | 责任角色 | 主要产物 |
|-----------|----------|----------|
| 任务拆解 / 阶段顺序 / 返工门禁 | `planner` | 阶段计划、依赖图、go/no-go 规则 |
| 后端 schema / API / tests | `worker` | model、migration、schema、service、router、focused tests |
| 前端 composable / 页面接线 / build | `worker` | API client、`useAnalytics`、5 页面埋点接入 |
| 审核与返工裁决 | `reviewer` | findings、风险、go/no-go |
| 文档 / 进度汇报 / 验收留痕 | controller | contract、tracker、acceptance artifact、阶段汇报 |

## 并行边界

- `P0` 完成前，不允许并行开发
- `P1` 后端完成契约实现后，`P2` 才能开始
- 文档留痕可以从 `P0` 开始并持续更新
- reviewer 介入点:
  - `P1` 完成后做后端 gate
  - `P2` 完成后做集成 gate
  - `P3` 做最终 acceptance gate

## 返工触发条件

- 事件类型、字段名或失败语义偏离 `M2_EVENT_CONTRACT.md`
- `event_data` 出现任意 shape、自由透传或未受控字段
- 引入 raw IP、token、email、password、备注文本等越界数据
- track 写入异常向业务主流程冒泡
- 限流无法跨请求稳定工作，或只靠前端节流“假装限流”
- 没有 focused tests、没有前端构建结果、没有 SQL 验证样本
- 回滚边界不清晰，无法回答“撤回 M2 需要删什么、停什么、回退什么”

## M2 可验收停止条件

满足以下条件后，本轮停止并汇报 `M2 可以验收`:

- `user_events` migration 可从当前 accepted existing-schema 起点执行
- `POST /api/v1/events/track` 可用，非法 payload 被拒绝
- 写入失败不会阻塞主流程，且返回语义与文档一致
- 5 个核心页面已接入首波 6 类事件
- 至少 1 条端到端手工链路可通过 SQL 查到完整事件序列
- 后端 focused tests 通过
- 前端 `typecheck` / `build` 通过
- reviewer 给出 `go` 结论
- `artifacts/M2_ACCEPTANCE.md` 已补齐测试命令、手工路径、SQL 样本与回滚边界
