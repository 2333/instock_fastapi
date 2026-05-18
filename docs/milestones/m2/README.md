# M2 文档索引

`M2` 对应 `P3-01` 用户行为埋点。该里程碑已于 `2026-04-20` 完成首波验收，当前不再作为 active execution pack 继续扩写；后续若需要恢复上下文，应先看验收记录，再转到 `Pre-M3` 主线对齐修复。

文档使用顺序:

- `docs/EXECUTION_PLAN.md`：主路线与 milestone 级 source of truth
- [artifacts/M2_ACCEPTANCE.md](./artifacts/M2_ACCEPTANCE.md)：当前关闭 `M2` 的验收记录、测试命令、手工链路、SQL 样本与回滚边界
- [M2_KICKOFF_PLAN.md](./M2_KICKOFF_PLAN.md)：`M2` 执行包，定义阶段、门禁、返工条件与停止条件
- [M2_EVENT_CONTRACT.md](./M2_EVENT_CONTRACT.md)：事件白名单、隐私边界、请求契约与查询口径
- [../m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md](../m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md)：`M2` 之后的当前 active 执行入口

当前使用约定:

- `M2` 已达成“可以验收”，不要再把仓库当前状态写成 `M2 kickoff 前`
- 如果问题涉及生产 500、schema drift、主线残留或发布门禁，不在 `M2` 目录内补锅，直接进入 `m3/Pre-M3` 执行包
- 首波只覆盖认证用户，不在本轮引入访客 / session 级事件
- 首波事件只允许白名单字段，不接收任意 shape 的 `event_data`
- 写入失败不得影响业务主流程，但失败事实必须可观测、可留痕
- `M2` 已通过 reviewer gate；下一阶段不是直接启动 `M3`，而是先完成 `Pre-M3` 对齐修复
