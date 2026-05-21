# M5 Artifacts

本目录用于记录 `M5 / P3-05` 执行过程中的证据和恢复材料。

Artifact 只记录证据，不承担路线裁决。当前路线裁决以：

1. `docs/EXECUTION_PLAN.md`
2. `docs/milestones/m5/README.md`
3. `docs/milestones/m5/M5_P3-05_KICKOFF_PLAN.md`

为准。

每个 artifact 必须回链到治理链路，并至少包含：

- 日期和执行者
- alignment note 链接或 ID
- 目标和 scope
- write set 与 changed files
- dependencies 和 non-goals
- acceptance
- rollback boundary
- evidence plan
- 命令与结果
- reviewer result：`approved` / `changes requested` / `no-go`
- follow-ups / out-of-scope residue

Stop rule：

- 没有 planner 认可的 alignment note，不得开始 implementation。
- scope 漂移、跨 WS 写集串改、依赖失效、证据与 acceptance 不对应、review finding 未关闭时，当前 WS 不得推进到下一个 implementation slice。
