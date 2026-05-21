# M3 文档索引

`m3/` 目录现在承接两类内容：

- 已关闭的 `Pre-M3` baseline：作为进入 `M3` 前的 release/runtime/doc 对齐证据保留
- 已关闭的 `M3 / P3-03` baseline：保留“参数化指标筛选 + 订阅提醒”最小闭环、post-merge staging 与 release 证据

## 历史查阅入口

- [docs/EXECUTION_PLAN.md](../../EXECUTION_PLAN.md) - 当前里程碑位置、主路线状态和高层 stop condition；现行 active route 不在 `m3/`
- [M3_P3-03_ALERT_ENGINE_PLAN.md](./M3_P3-03_ALERT_ENGINE_PLAN.md) - `M3 / P3-03` closed baseline 的锚定目标、canonical model、分步交付、验收与 PR 收口清单
- [PRE_M3_MAINLINE_ALIGNMENT_PLAN.md](./PRE_M3_MAINLINE_ALIGNMENT_PLAN.md) - 回看 `Pre-M3` 的步骤、分工、依赖顺序和恢复规则
- [PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md](./PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md) - 回看 `Pre-M3` 的最终真相、blocker closure 和交接入口
- `docs/milestones/phase3/PHASE3_P3-03_ALERT_ENGINE*.md` - `M3 / P3-03` 的设计输入

## Gate / Support 文档

- [PRE_M3_DECISION.md](./PRE_M3_DECISION.md) - 只在 `W5` / `M3` 放行裁决时再看，不承担日常推进导航
- [artifacts/README.md](./artifacts/README.md) - wave artifact 记录规范；artifact 只用于证据和恢复，不承担路线裁决

## 使用顺序

1. 先看 `docs/EXECUTION_PLAN.md`
2. 需要回看 `M3 / P3-03` 已完成边界时，再看 [M3_P3-03_ALERT_ENGINE_PLAN.md](./M3_P3-03_ALERT_ENGINE_PLAN.md)
3. 如果要确认为什么当时可以启动 `M3`，再看 [PRE_M3_DECISION.md](./PRE_M3_DECISION.md)
4. 如果要回看 `Pre-M3` 的关闭证据，再看 [PRE_M3_MAINLINE_ALIGNMENT_PLAN.md](./PRE_M3_MAINLINE_ALIGNMENT_PLAN.md) 和 [PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md](./PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md)
5. 需要设计细节时，再读 `docs/milestones/phase3/PHASE3_P3-03_ALERT_ENGINE*.md`
6. 只有需要证据、命令、变更清单或执行中断恢复时，才进入 `artifacts/`

## 角色约定

- `README`：只做入口，不重复写状态真相。
- `PLAN`：只写步骤、依赖、分工、write set 和恢复规则。
- `TRACKER`：只写当前真相、blocker、下一步。
- `DECISION`：只写 gate 和 `go / no-go`。
- `artifacts/`：只写工作内容、证据和留痕。

## 与 `M3 / P3-03` 的关系

- `P3-03` 设计输入仍来自 `docs/milestones/phase3/PHASE3_P3-03_ALERT_ENGINE*.md`
- `Pre-M3` 已在 `2026-04-22` 通过最终 gate；`M3 / P3-03` 也已完成 post-merge staging 收尾，因此这里现在是 closed baseline 目录
- `Pre-M3` 的 plan / tracker / decision 继续保留，但只作为 closed baseline 与 gate evidence，不再代表当前 blocker
- 当前 `M3` 的唯一锚点是：`Saved Screener` 为 authored truth source，`Alert Subscription` 为提醒绑定，`Registry` 为字段目录，`Adapter` 为可替换执行层
- 当前 `M3-A` 已完成到参数化 `RSI / MACD / BOLL` runtime + `Selection` 最小前端接线 + live smoke
- 当前 `M3-B/S1-S4` 已完成后端订阅、最小用户入口、手动触发、run/hit、站内摘要通知、盘后 scheduler/checker 与 reviewer closure
- 当前状态是 `M3` 已完成 post-merge staging 收尾；`M3-C` 快捷入口收敛为验收后增强项，暂不扩散到铃铛、邮件或 Attention 快捷入口
