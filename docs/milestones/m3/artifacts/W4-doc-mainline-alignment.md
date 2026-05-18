# W4 Doc Mainline Alignment

> Status: completed
> Owner: controller
> Depends: `W1`, `W2`, `W2a`, `W2b`, `W3`
> Last updated: 2026-04-22

## 目标

基于 `W1` ~ `W3` 与 `W2b` 的真实结果，完成主线文档的最终收口，让仓库能明确回答“当前在哪、下一步做什么、如果中断如何恢复”，同时把路线文档收敛到 3 个核心入口。

## Core route docs

`W4` 完成后，当前主路线只保留以下 3 份 route docs：

1. `docs/EXECUTION_PLAN.md`
2. `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`
3. `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`

`docs/milestones/m3/PRE_M3_DECISION.md` 继续保留，但只承担 gate / close-condition 角色，不承担日常路线导航。
wave artifact 继续承担恢复和留痕角色，不承担路线裁决。

## Write set

- `docs/EXECUTION_PLAN.md`
- `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`
- `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`
- `docs/milestones/m3/PRE_M3_DECISION.md`
- `docs/README.md`
- `docs/milestones/m3/README.md`
- 本 artifact

## 本轮范围

1. 把 `docs/README.md` 收敛为 4 层：主推进文档、当前执行包、工作内容/留痕、参考/设计资产。
2. 在 `docs/EXECUTION_PLAN.md` 顶部补“文档约定”，明确 `M*` 只负责执行/验收，`Phase*` 只负责设计编号。
3. 收紧 `docs/milestones/README.md` 与 `docs/milestones/m3/README.md` 的入口角色，避免 `README/PLAN/TRACKER/DECISION` 互相抢入口。
4. 给 `phase3/phase4` 和 `audit/residue` 两类高频误导文档补 banner，明确它们不是当前主线推进入口。

## Changed files

- `docs/README.md`
- `docs/EXECUTION_PLAN.md`
- `docs/deployment/release_workflow.md`
- `docs/milestones/README.md`
- `docs/milestones/m3/README.md`
- `docs/milestones/phase3/README.md`
- `docs/milestones/phase4/README.md`
- `docs/milestones/phase4/PHASE4_PLANNING.md`
- `docs/archive/README.md`
- `docs/archive/phase4/PHASE4_PLANNING_2026-04-04.md`
- `docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md`
- `docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md`
- `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`
- `docs/milestones/m3/PRE_M3_DECISION.md`

## Commands run

- `sed -n '1,240p' docs/README.md`
- `sed -n '1,260p' docs/EXECUTION_PLAN.md`
- `sed -n '1,240p' docs/deployment/release_workflow.md`
- `sed -n '1,220p' docs/milestones/README.md`
- `sed -n '1,220p' docs/milestones/m3/README.md`
- `sed -n '1,220p' docs/milestones/phase3/README.md`
- `sed -n '1,220p' docs/milestones/phase4/README.md`
- `sed -n '1,220p' docs/milestones/phase4/PHASE4_PLANNING.md`
- `sed -n '1,220p' docs/archive/phase4/PHASE4_PLANNING_2026-04-04.md`
- `sed -n '1,220p' docs/archive/README.md`
- `sed -n '1,200p' docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md`
- `sed -n '1,200p' docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md`
- `git status -sb`
- `git diff --stat -- docs/README.md docs/EXECUTION_PLAN.md docs/deployment/release_workflow.md docs/milestones/README.md docs/milestones/m3/README.md docs/milestones/phase3/README.md docs/milestones/phase4/README.md docs/milestones/phase4/PHASE4_PLANNING.md docs/archive/README.md docs/archive/phase4/PHASE4_PLANNING_2026-04-04.md docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md docs/milestones/m3/artifacts/W4-doc-mainline-alignment.md`
- `rg -n '唯一 \`plan-of-record\`|当前 active 路线是 \`Pre-M3|设计资产目录|不是当前主线推进入口|当前推进状态一律先看' docs/README.md docs/EXECUTION_PLAN.md docs/milestones/README.md docs/milestones/m3/README.md docs/milestones/phase3/README.md docs/milestones/phase4/README.md docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md`
- `rg -n 'M2 / P3-01 kickoff 前|temporary restriction|下一阶段从 \`M2 / P3-01' docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md docs/deployment/release_workflow.md docs/milestones/phase4/PHASE4_PLANNING.md docs/archive/phase4/PHASE4_PLANNING_2026-04-04.md`

## Results

- `docs/README.md` 现在明确给出“从哪里开始看”的固定阅读顺序。
- `docs/EXECUTION_PLAN.md` 现在显式声明自己是唯一 `plan-of-record`，并把 `M*` 与 `Phase*` 的角色分开。
- `docs/milestones/README.md` 现在把 `m3/` 定义为当前 active 执行包，把 `m0/m1/m2` 降级为历史执行包，把 `phase3/phase4` 定义为设计资产。
- `docs/milestones/m3/README.md` 现在把 `README/PLAN/TRACKER/DECISION/artifacts` 的角色拆开，不再互相抢入口。
- `phase3/phase4` 与 `audit/residue` 页面补了非主线入口 banner，减少搜索命中误导。
- `docs/deployment/release_workflow.md` 现在与 `PRE_M3_DECISION.md` 的 release gate 口径一致，不再保留旧的 `W1 closes` / temporary restriction 表述。
- `docs/milestones/phase4/PHASE4_PLANNING.md`、`docs/archive/phase4/PHASE4_PLANNING_2026-04-04.md`、`docs/archive/README.md` 已明确降级为历史/规划资产，不再充当当前执行入口。
- `reviewer` 终审结论：no findings on remaining documentation-consistency issues。
- `code-review-expert` 二次 review 结论：未发现新的 blocking finding；剩余风险只在历史正文仍保留旧时代内容，但入口已被降级并注明。

## Open risks

- 旧执行包内部仍保留历史命名和历史表述；这轮没有逐篇重写。
- 搜索结果仍可能先命中 artifact 或分析文档，但这些页面现在至少会先提示“不是主线推进入口”。
- `W5` 还没执行，所以 `Pre-M3` 整体仍未放行；当前只是完成了文档主线终扫。

## Remaining doc drift

- 当前主推进入口已收敛；剩余漂移主要位于历史文档正文内部，不再作为当前执行 blocker。

## Next step

1. 进入 `W5 reviewer gate`。
2. 由 reviewer 基于 `W1` ~ `W4` 的当前 artifact 决定 `Pre-M3` 是否可放行。

## Blocked by

- -

## Recovery note

- 如果从这里恢复，先确认 `W2b` 是否已按 active-path scope 关闭、`W3` 是否已经把 active residue 收口完，再进入文档终扫。
- `W4` 不应扩散新文档；优先修改现有入口文档和当前执行包。

## Required records

- Changed files
- Commands run
- Results
- Open risks
- Remaining doc drift
- Next step
- Blocked by
- Recovery note
