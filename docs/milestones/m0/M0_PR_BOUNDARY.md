# M0 基线冻结：可合并 PR 边界定义

> 版本: 2026-04-05
> 目标: 从 `phase-0-complete-scanning-engine` 分支切出 `M0` 合并包，明确保留范围与延后范围

---

## 分支现状

| 分支 | 最新提交 | 说明 |
|------|---------|------|
| `main` | c68a3f2 | 初始 6 个 PR 合并（Phase 0a 核心） |
| `phase-0-complete-scanning-engine` | b9e3b48 | 包含 Phase 0b + Phase 1 + Phase 2/3 预实现 |

**关键判断**：当前长分支已同时包含 Phase 0b、Phase 1、Phase 2、Phase 3 多阶段改动，不再适合作为单一承载分支继续叠需求。必须按里程碑拆分。

---

## M0 范围：Phase 0/1 基线（必须包含）

M0 目标是冻结“筛选 → 回测 → Dashboard”主线能力，形成稳定基线并合入 `main`。

### Phase 0a - 最小可用闭环（已全部完成）

| 任务 | 关键提交/文件 | 验收状态 |
|------|--------------|----------|
| P0a-01 SelectionService 收敛 | `0b6389f`（已合并到 main） | ✅ |
| P0a-02 命中证据标准化 | `d92b7fe`（已合并到 main） | ✅ |
| P0a-03 个股详情聚合接口 | 已合并到 main | ✅ |
| P0a-04 三层边界 | MarketDataProvider 抽象层 | ✅ |
| P0a-05 前端筛选面板 | `Selection.vue` | ✅ |
| P0a-06 前端结果列表 | `Selection.vue` 集成 | ✅ |
| P0a-07 前端个股详情 | `StockDetail.vue` | ✅ |

**M0 包含**：上述全部功能（已在 `main` 中，无需额外操作）。

---

### Phase 0b - 日常可用（M0 必须补齐的收尾）

| 任务 | 当前状态 | M0 动作 |
|------|----------|---------|
| P0b-01 Dashboard 4 卡片联调 | ✅ 已记录（2026-04-04 容器内验证） | **保留**：联调记录已写入 EXECUTION_PLAN.md |
| P0b-02 筛选条件保存/加载 | ✅ `06c6fdb`（在长分支上） | **保留**：CRUD 端点 + 前端集成 |
| P0b-03 关注列表联动 | ✅ `2e03a0b`（在长分支上） | **保留**：结果页"加入关注"按钮 |
| P0b-04 扫描历史记录 | ✅（在长分支上） | **保留**：历史查看与对比 |
| P0b-05 清理废弃代码 | ✅ `selection_service_with_provider.py` 已删除 | **保留**：清理完成 |
| P0b-06 形态筛选条件 | ⚠️ 部分完成（单形态支持，多形态待评估） | **保留**：当前能力已可用，多形态作为增强延后 |

**M0 包含**：P0b-01 ~ P0b-05 全部保留；P0b-06 保留当前单形态能力，多形态评估延后 Phase 2。

---

### Phase 1 - 策略验证闭环（M0 必须包含）

Phase 1 已于 2026-04-03 完成 DoD 验收，全部功能已在长分支实现。

| 任务 | 关键提交 | M0 动作 |
|------|---------|---------|
| P1-00 Strategy.params 契约统一 | 多提交（`ae03821` 等） | **保留**：统一 envelope |
| P1-01 筛选 → 策略打通 | 多提交 | **保留**：一键保存为策略 + Backtest 承接 |
| P1-02 回测报告结构化 | 多提交 | **保留**：schema 化报告 |
| P1-03 策略参数对比 | `1abb04f`（对比契约统一） | **保留**：对比页 + URL 状态 |
| P1-04 回测异步化 | `5e31cef`（后台任务基础设施） | **保留**：异步任务 + 状态跟踪 |
| P1-05 策略保存与 URL 化 | 多提交 | **保留**：URL 即状态 |

**M0 包含**：Phase 1 全部功能（作为 Phase 0 后续能力自然延伸）。

---

## 延后范围：不属于 M0

以下能力已在当前长分支实现，但**不属于** M0 基线，应延后至对应里程碑：

| 延后项 | 对应里程碑 | 说明 |
|--------|-----------|------|
| Phase 2 体验打磨（所有任务） | M2+ | 交互优化、虚拟滚动、多周期切换等属于体验层，不阻塞基线 |
| Phase 3 全部 6 个 P3 功能 | M2~M7 | P3-01/03/04/05/06 已在长分支预实现，但需按 milestone 独立验收 |
| 数据层改造（Phase 1.5 / M1） | M1 | TimescaleDB、Alembic、新接口接入独立为 M1 milestone |
| 10 个交易日稳定性持续验证 | M0 期间或 M1 | 作为观察项，非功能门槛待决策 |

**关键决策**：当前长分支上的 Phase 2/3 代码虽然是"已完成"状态，但必须：
1. 从 M0 合并包中剥离（不在 M0 PR 内）
2. 在后续 milestone 独立验证后分别合并

---

## M0 PR 边界操作清单

### 1. 确定基准点

- M0 基线基准：以当前 `phase-0-complete-scanning-engine` 的 `b9e3b48` 为基准
- 保留范围：从初始 commit 到 `b9e3b48` 中属于 Phase 0/1 的所有改动
- 延后范围：Phase 2/3 相关文件（见下表）从 M0 PR 中剔除（或标记为 WIP）

### 2. 文件级范围划分

**M0 包含的文件**（Phase 0/1 核心）:
```
app/
  ├── api/routers/ (除 Phase 3 新增路由外，全部)
  ├── services/ (selection_service, backtest_service, strategy_service 等)
  ├── schemas/ (selection_schema, strategy_schema, backtest_schema 等)
  ├── core/dependencies.py (auth 增强)
  ├── database.py (当前 SQLite + PG 兼容层)
  └── config.py
web/
  ├── src/views/Dashboard.vue (4 卡片)
  ├── src/views/Selection.vue (筛选 + 结果)
  ├── src/views/StockDetail.vue
  ├── src/views/Backtest.vue (基础回测 + 对比，不含 Phase 3 标签页)
  └── src/components/ (相关组件)
tests/ (全部 132 个测试)
docs/
  ├── EXECUTION_PLAN.md (M0 收敛后版本)
  ├── DATA_LAYER_REPORT.md (Phase 1.5 设计，但 M0 不实现，仅文档)
  └── PRD/ROADMAP (如有)
```

**M0 延后的文件**（Phase 2/3 相关，从 M0 PR 剔除或标记为后续 milestone）:
```
web/src/views/Backtest.vue:
  - 公共策略标签页 (public-strategies)
  - 参数优化标签页 (optimization-tab)
  - 数据洞察标签页 (reports)
  - 通知铃铛相关集成

web/src/components/:
  - StrategyCard.vue (P3-04)
  - OptimizationCard.vue (P3-05)
  - ReportCard.vue (P3-06)
  - AlertBell.vue (P3-03)

app/api/routers/:
  - 若新增 P3-01/03/04/05/06 专属端点，延后

app/services/:
  - alert_service.py (P3-03)
  - report_service.py (P3-06)
  - optimization_service.py (P3-05)
  - strategy_market_service.py (P3-04)
  - user_event_service.py (P3-01)
```

### 3. 代码路径约束

Backtest.vue 文件同时包含 Phase 1 和 Phase 3 代码，需要：
- **M0 保留**：基础回测流程（参数配置 → 执行 → 结果显示 → 历史对比）
- **M0 延后**：`strategySourceTab === 'public'` 分支、`optimization-tab` 分支、`reports` 分支

**操作方法**：
- 方案 A（推荐）：在 M0 PR 中暂时注释或 `v-if="false"` 隐藏 Phase 3 标签页，后续 milestone 再启用
- 方案 B：在 M0 PR 中直接删除 Phase 3 相关代码块，后续从长分支 cherry-pick

### 4. 数据库迁移

- M0 不引入新迁移（Phase 0/1 使用 `init_db()` auto-create）
- M1 的 Alembic 迁移延后至 M1 milestone

### 5. 文档与验收

- M0 PR 描述必须引用本边界文档
- M0 验收仅检查 Phase 0/1 功能：
  - 扫描 → 结果 → 详情链路
  - Dashboard 4 卡片
  - 条件保存/加载
  - 关注联动
  - 回测报告与对比
- Phase 2/3 功能在 M0 验收时明确标记为"未激活/延后"

---

## M0 PR 创建步骤（建议）

1. 从 `phase-0-complete-scanning-engine` 创建 `m0-baseline-freeze` 分支
2. 根据上述文件范围，清除或禁用 Phase 2/3 代码（保持编译通过但不可用）
3. 运行完整测试（132 个）确保无回归
4. 运行前端构建与类型检查
5. 更新 CHANGELOG 为 M0 合并包
6. 提交 PR 到 `main`，标题：`[M0] Phase 0/1 Baseline Freeze`
7. PR 描述中附上本边界文档链接

---

## 回滚边界

- **数据库**：M0 无 schema 变更，回滚即代码回退，无需数据迁移
- **前端**：M0 仅收敛现有功能，回滚不影响既有用户（未发布新功能）
- **API**：M0 不新增端点版本，保持向后兼容

---

## 决策待办（人工）

| 事项 | 选项 | 影响 |
|------|------|------|
| M0-05 10 日稳定性 | A: 硬门槛（延迟 M0 2 周） B: 观察项（M0 立即冻结） | 决定 M0 是否可立即合并 |
| Phase 2/3 代码处理 | A: 保留但禁用 B: 删除后后续增量开发 | 影响 M0 代码整洁度 |

**建议**：选择 B（观察项）+ A（禁用保留），M0 快速冻结，Phase 2/3 延后 milestone 独立验收。

---

**文档状态**: 草案，待 Opus 确认后执行。
