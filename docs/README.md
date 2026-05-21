# InStock 文档中心

如果你只想知道“项目当前做到哪、下一步做什么、我该从哪里开始看”，先按这个顺序读：

1. [EXECUTION_PLAN.md](./EXECUTION_PLAN.md)
2. [milestones/m5/README.md](./milestones/m5/README.md)
3. [milestones/m5/M5_P3-05_KICKOFF_PLAN.md](./milestones/m5/M5_P3-05_KICKOFF_PLAN.md)

## 文档分层

### 1. 主推进文档

- [EXECUTION_PLAN.md](./EXECUTION_PLAN.md)：唯一 `plan-of-record`。当前做到哪、下一步做什么、哪个执行包是 active，一律先看这里。

### 2. 当前执行包文档

- [milestones/m5/README.md](./milestones/m5/README.md)：当前 active 执行包入口，负责说明 `M5 / P3-05` 参数优化的启动边界、依赖顺序和停机点。
- [milestones/m5/M5_P3-05_KICKOFF_PLAN.md](./milestones/m5/M5_P3-05_KICKOFF_PLAN.md)：当前 `M5` 的 kickoff 计划、并行任务拆分、验收和回滚边界。
- [milestones/m5/M5_P3-05_REVIEW_CHECKLIST.md](./milestones/m5/M5_P3-05_REVIEW_CHECKLIST.md)：`M5` 启动前与实现前的 reviewer 检查清单。

### 3. 工作内容与留痕文档

- [milestones/README.md](./milestones/README.md)：执行包总索引，包含 `m0/`、`m1/`、`m2/`、`m3/`、`m5/` 和设计资产目录的定位说明。
- [milestones/m0/](./milestones/m0/)、[milestones/m1/README.md](./milestones/m1/README.md)、[milestones/m2/README.md](./milestones/m2/README.md)、[milestones/m3/README.md](./milestones/m3/README.md)：历史执行包与验收材料入口。
- [milestones/m5/artifacts/README.md](./milestones/m5/artifacts/README.md)：当前执行包的 artifact 记录规范。
- [REBASELINE_M0_PLAN.md](./REBASELINE_M0_PLAN.md)、[REBASELINE_M0_TRACKER.md](./REBASELINE_M0_TRACKER.md)：`M0 rebaseline` 的历史治理记录。
- [PROJECT_MAINLINE_AUDIT_2026-04-20.md](./PROJECT_MAINLINE_AUDIT_2026-04-20.md)、[RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md](./RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md)：分析、审计和残留清单，不是当前主推进入口。

### 4. 参考与设计资产

- [PRD.md](./PRD.md)：v2.0 产品需求文档，定义产品定位、目标用户、功能边界和长期目标。
- [ROADMAP.md](./ROADMAP.md)：v2.0 路线图，负责产品阶段方向，不直接承担当前执行状态。
- [milestones/phase3/README.md](./milestones/phase3/README.md)、[milestones/phase4/README.md](./milestones/phase4/README.md)：设计/规划资产，不代表当前应该启动或已经完成。
- [archive/README.md](./archive/README.md)：v1 历史归档文档。
- [architecture/system_architecture.md](./architecture/system_architecture.md)、[design/class_diagram.md](./design/class_diagram.md)、[api/api_document.md](./api/api_document.md)、[api/integration_report.md](./api/integration_report.md)、[deployment/compose_environments.md](./deployment/compose_environments.md)、[deployment/release_workflow.md](./deployment/release_workflow.md)：技术、接口和部署参考资料。

## 当前约定

- `M*` 表示实际推进/验收里程碑，当前状态和完成度只在 `M*` 体系里写。
- `Phase*` 表示能力设计编号或历史规划资产，不单独代表当前执行状态。
- 当前 active 路线是 `M5 / P3-05` 参数优化 kickoff；`Pre-M3` 与 `M3` 已作为 closed baseline 保留在 `docs/milestones/m3/`。
- 当前 `M5` 的启动锚点是：复用现有 `BacktestService` 与异步回测任务模式，先交付参数优化最小闭环；不默认引入 Celery/RQ，也不把孤立算法原型视为 runtime-ready 能力。

## 代码结构对应关系

- `app/`：FastAPI 后端入口、路由、服务层和数据库层。
- `core/`：数据采集、技术指标、形态识别、策略和回测实现。
- `web/`：Vue 前端工程，以及后端根路径使用的静态首页资源。
- `scripts/`：环境初始化、数据库准备和辅助脚本。
