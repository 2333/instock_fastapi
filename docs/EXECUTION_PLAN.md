# InStock 执行计划（Execution Plan）

> 版本：v2.0 | 更新日期：2026-04-01
> 基于 PRD v2.0 / ROADMAP v2.0 + 代码实际进度重写
> v1.0 归档：[EXECUTION_PLAN_v1_archive.md](./EXECUTION_PLAN_v1_archive.md)

---

## 如何使用本文档

本计划是 **vibe-coding 的执行指南**：
- 每个任务都标注了 **状态**、**涉及文件**、**验收标准**
- Agent 或开发者拿到一个任务即可开工，不需要额外上下文
- 任务按依赖关系排序，从上到下执行
- `[x]` = 已完成，`[-]` = 部分完成，`[ ]` = 待做

---

## 代码资产现状快照（2026-04-01）

| 能力 | 状态 | 关键文件 |
|------|------|---------|
| 数据更新调度器 | ✅ 完成 | `app/scheduler/` |
| 股票基础 API（11 个 router，41 个端点） | ✅ 完成 | `app/api/routers/` |
| SelectionService 统一 | ✅ 完成 | `app/services/selection_service.py`（旧 `selection_service_with_provider.py` 已废弃） |
| 命中证据结构化输出 | ✅ 完成 | `app/schemas/selection_schema.py` — ScreeningEvidenceItem / SelectionResultItem |
| MarketDataProvider 抽象层 | ✅ 完成 | `app/services/market_data_provider.py` |
| 策略模板 CRUD | ✅ 完成 | `app/api/routers/strategy_router.py` |
| 回测引擎 + 报告 | ✅ 完成 | `app/services/backtest_service.py` + `backtest_router.py` |
| 关注列表（分组/备注/提醒条件） | ✅ 完成 | `app/api/routers/attention_router.py` |
| 市场概览 API | ✅ 完成 | `app/api/routers/market_router.py` |
| 用户认证 JWT | ✅ 完成 | `app/api/routers/auth_router.py` |
| 前端 Vue 3 SPA（10 个主视图） | ✅ 完成 | `web/src/views/` |
| 选股页 + 关注按钮 | ✅ 完成 | `web/src/views/Selection.vue` |
| 回测页 | ✅ 完成 | `web/src/views/Backtest.vue` |
| 个股详情页 | ✅ 完成 | `web/src/views/StockDetail.vue` |
| Dashboard | ✅ 完成 | `web/src/views/Dashboard.vue` |
| 测试覆盖 | ⚠️ 部分 | `tests/`（10 个测试文件，核心 router 100%，service ~67%） |

---

## Phase 0a：最小可用闭环

### 验收标准
> 用户在筛选页选择"MACD 金叉 + 成交量放大"，点击扫描，看到命中结果列表（含命中原因摘要），点击某只股票进入详情页查看 K 线和命中证据。

### 任务清单

#### P0a-01：收敛 SelectionService [x]
- **已完成** @ commit `0b6389f`
- 合并 SelectionService 和 SelectionServiceWithProvider 为统一类
- `app/services/selection_service.py` 支持 provider 模式和 SQL fallback

#### P0a-02：标准化命中证据输出 [x]
- **已完成** @ commit `d92b7fe`
- `ScreeningEvidenceItem` 包含 key/label/value/operator/condition/matched/condition_id/condition_name/description
- `SelectionResultItem` 包含 evidence 数组 + reason_summary + score + signal
- 符合 PRD 2.2 定义

#### P0a-03：个股详情聚合接口 [x]
- **已完成**
- `stock_router GET /stocks/{code}` + `indicator_router` + `pattern_router` 提供完整数据
- 前端 `StockDetail.vue` 聚合展示 K 线 + 指标 + 形态

#### P0a-04：router → service → engine 三层边界 [x]
- **已完成** @ commit `6233d5c`
- MarketDataProvider 抽象层已引入
- 调用方向单一：router → service → engine/provider

#### P0a-05：前端筛选面板页 [x]
- **已完成**
- `web/src/views/Selection.vue`（40KB）
- 条件选择 + 参数配置 + 执行扫描 + 条件模板 + 历史比较

#### P0a-06：前端结果列表页 [x]
- **已完成**
- 集成在 `Selection.vue` 中
- 命中卡片展示：股票名称、代码、命中条件摘要、匹配度、关注按钮

#### P0a-07：前端个股详情页 v1 [x]
- **已完成**
- `web/src/views/StockDetail.vue`（33KB）
- K 线 + 成交量 + 指标叠加 + 形态标注 + 命中证据

**Phase 0a 状态：✅ 全部完成**

### 非功能性门槛

| 指标 | 要求 | 状态 |
|------|------|------|
| 全市场扫描响应时间 | < 30s（5000 股 × 3 条件） | [ ] 待验证 |
| 数据更新稳定性 | 连续 5 个交易日 100% | [ ] 待验证 |
| 扫描结果正确性 | 抽查 10 只命中股票，证据与实际数据一致 | [ ] 待验证 |

---

## Phase 0b：日常可用

### 验收标准
> 用户每天盘后打开 InStock，首页看到市场概况，进入筛选页加载上次保存的条件一键扫描，命中股票可一键加入关注列表。

### 任务清单

#### P0b-01：首页市场概览（4 卡片） [-]
- **文件**：`web/src/views/Dashboard.vue`
- **后端**：`market_router` / `selection_router` 已提供 Dashboard 所需聚合端点
- **现状**：Dashboard.vue 已切换为 4 卡片工作台布局，前端已接入真实 API；当前剩余工作主要是联调验证与文案/口径细修
- **已完成**：
  - [x] 卡片 1 — 市场温度计：涨跌家数、涨停跌停、主要指数涨跌、情绪摘要
  - [x] 卡片 2 — 我的关注：关注列表 + 今日命中提示
  - [x] 卡片 3 — 今日扫描发现：已保存筛选条件命中概要 + 跳转入口
  - [x] 卡片 4 — 策略信号/回测更新：最近回测摘要
- **后端补充**：
  - [x] `GET /api/v1/market/summary` — 返回涨跌家数、涨停跌停、主要指数等聚合数据
  - [x] `GET /api/v1/selection/today-summary` — 返回已保存条件的今日命中概要
- **待做**：
  - [ ] 实际联调确认 4 张卡片在真实登录态/真实数据下展示稳定
  - [ ] 校正 Dashboard 文案与 PRD 验收描述，避免计划文档继续落后于代码
- **已验证**：
  - [x] `tests/test_market_summary.py` 已覆盖 `GET /api/v1/market/summary`
  - [x] `tests/test_selection_today_summary.py` 已覆盖 `GET /api/v1/selection/today-summary`
- **验收**：打开首页能看到 4 张卡片，每张卡片数据来自真实 API，点击可跳转到对应功能页

#### P0b-02：筛选条件保存/加载 [x]
- **已完成** @ commit `06c6fdb`
- `selection_router` 已有 `/selection/my-conditions` CRUD 端点
- 前端已集成条件保存/加载/模板功能

#### P0b-03：关注列表联动 [x]
- **已完成** @ commit `2e03a0b`
- 结果列表页已集成"加入关注"按钮
- `attention_router` 支持分组/备注/提醒条件

#### P0b-04：扫描历史记录 [x]
- **已完成**
- `selection_router GET /screening/history` + `POST /screening/compare`
- 前端已集成历史查看和对比功能

#### P0b-05：清理废弃代码 [x]
- **文件**：`app/services/selection_service_with_provider.py`
- **已完成**：
  - [x] 已删除 `selection_service_with_provider.py`
  - [x] 源码 / 测试中的相关 import 已清理
  - [x] 本轮 heartbeat 已清理 `__pycache__` 并重新验证，`grep -R --exclude-dir='__pycache__' "selection_service_with_provider" app tests` 无结果
- **验收**：`grep -R --exclude-dir='__pycache__' "selection_service_with_provider" app tests` 无结果

#### P0b-06：形态筛选条件集成 [ ]
- **文件**：`app/schemas/selection_schema.py`（line 92-98 标注 "coming soon"）
- **待做**：
  - [ ] 在筛选条件中支持形态过滤（如"出现双底"、"头肩底"）
  - [ ] 将 `pattern_service` 的形态结果作为筛选条件
  - [ ] 前端筛选面板增加形态条件选项
- **验收**：用户可选择"MACD 金叉 + 头肩底形态"组合条件进行扫描

---

## Phase 0 整体 DoD（进入 Phase 1 的门槛）

- [x] 扫描 → 筛选 → 验证 主线完整可用
- [-] 首页市场概览 4 卡片可展示
- [x] 筛选条件可保存/加载/复用
- [x] 关注列表可从扫描结果中添加
- [ ] 全市场扫描响应时间 < 30s
- [ ] 数据更新连续 10 个交易日稳定
- [ ] 核心 schema 和 service 模块测试覆盖率 > 60%

---

## Phase 1：策略验证闭环

### 验收标准
> 用户把筛选方法转成参数化策略，跑历史回测，看到收益曲线、最大回撤、胜率、基准对比，并能对比不同参数版本的结果。

### 现状评估
后端策略模板和回测引擎骨架已完成（`strategy_service.py` + `backtest_service.py`），前端回测页已有 68KB 的综合 UI。核心差距在于：回测报告的结构化程度、策略-筛选条件的打通、基准对比的完整性。

### 任务清单

#### P1-01：筛选条件 → 策略模板打通 [ ]
- **文件**：`app/services/strategy_service.py`, `app/services/selection_service.py`
- **待做**：
  - [ ] 用户在筛选页可一键"将当前条件保存为策略"
  - [ ] 策略模板可直接消费筛选条件 schema
  - [ ] 在策略模板中增加买卖规则配置（入场条件 = 筛选条件，出场条件 = 可配置）
- **验收**：在筛选页保存一组条件 → 在策略页看到对应策略 → 可直接发起回测

#### P1-02：回测报告结构化 [-]
- **文件**：`app/services/backtest_service.py`, `app/schemas/`
- **现状**：回测引擎有基础实现，需确认输出是否完整
- **待做**：
  - [ ] 确认回测报告输出包含：收益曲线、最大回撤、胜率、盈亏比、年化收益率
  - [ ] 增加基准对比（沪深 300 / 上证指数）
  - [ ] 输出 schema 化的 JSON 结构（为未来 AI 解读预留）
  - [ ] 关键风险摘要（最大连续亏损天数、最大单日损失等）
- **验收**：回测结果页展示完整的报告，数据可信且可解释

#### P1-03：策略参数对比 [-]
- **文件**：`web/src/views/Backtest.vue`
- **现状**：前端已有回测 UI，需确认对比功能完整度
- **待做**：
  - [ ] 同一策略不同参数版本的回测结果并排对比
  - [ ] 核心指标对比表：收益率、回撤、胜率、夏普比率
  - [ ] 收益曲线叠加图
- **验收**：用户跑两次不同参数的回测 → 在对比页看到差异

#### P1-04：回测任务异步化 [ ]
- **文件**：`app/api/routers/backtest_router.py`, `app/services/backtest_service.py`
- **待做**：
  - [ ] 回测作为后台任务运行（大时间跨度回测可能耗时较长）
  - [ ] 前端轮询或 SSE 获取进度
  - [ ] 回测任务状态持久化（pending → running → completed / failed）
- **验收**：发起跨 1 年回测 → 前端显示进度 → 完成后自动刷新结果

#### P1-05：策略保存与 URL 化 [ ]
- **文件**：`app/api/routers/strategy_router.py`
- **现状**：策略 CRUD 已有
- **待做**：
  - [ ] 策略 + 参数 + 回测结果可通过 URL 复现
  - [ ] 前端 URL 即状态（刷新不丢失上下文）
- **验收**：复制回测结果页 URL → 新标签页打开 → 完整复现

---

## Phase 2：体验打磨（方向性，不定义具体任务）

### 目标
从"能用"到"顺手"。

### 方向
- 筛选面板交互优化（拖拽排序、条件组预设）
- 结果列表虚拟滚动 + 高级排序
- 个股详情页增强（多时间周期切换、指标自选）
- 关注列表提醒能力（条件触发推送）
- 最近研究上下文（"上次我在看什么"）

### 不做
- 通用笔记系统
- 项目式研究管理
- 社区分享

---

## 测试与质量

### 当前覆盖（10 个测试文件）
| 文件 | 覆盖范围 |
|------|---------|
| test_api.py | 全端点集成测试 |
| test_router_endpoints.py | 端点 mock 测试 |
| test_selection_market_services.py | 选股 + 市场服务 |
| test_backtest_service.py | 回测引擎 |
| test_stock_service.py | 股票服务 |
| test_pattern_service.py | 形态识别 |
| test_auth_router.py | 认证流程 |

### 待补充
- [ ] fund_flow_service 测试
- [ ] indicator_service 测试
- [ ] 选股引擎端到端测试（真实条件 → 真实结果 → 验证证据正确性）
- [ ] 回测报告结构测试
- [ ] 前端 E2E 测试（至少覆盖扫描 → 结果 → 详情主线）

---

## 暂不进入执行

| 事项 | 原因 |
|------|------|
| Parquet 每日导出 | 等 Phase 1 回测有性能瓶颈时再做 |
| DuckDB 迁移 | 同上 |
| AI 助手 | Phase 0-1 稳定运行后再接入 |
| 低代码策略编排器 | Phase 2+ |
| 移动端适配 | Phase 2+ |
| 多市场扩张 | 不在当前规划 |

---

## 当前分支工作流说明（2026-04-02 heartbeat）

- 当前工作分支 `phase-0-complete-scanning-engine` 上存在一批尚未合并的改动，范围已同时覆盖：
  - Phase 0b：首页 4 卡片 / 今日摘要 / 市场概览
  - Phase 1：筛选条件 → 策略模板打通
  - Phase 1：回测报告结构与前端回测页增强
- 这说明代码现实已经不是单一的“Phase 0b 收尾分支”，而是 **Phase 0b 收尾 + Phase 1 预实现并行态**。
- 后续 heartbeat / review / 提交时，必须按任务归属来判断是否推进偏航：
  - Phase 0b 目标：联调验收 + 非功能验证 + 形态筛选条件
  - Phase 1 目标：策略桥接、回测报告、参数对比
- 结论：当前不应把所有未提交改动都视为“Phase 0b 阻塞”，而应按 roadmap 分层审视。

## 下一步执行建议（优先级排序）

**立即可做（Phase 0b 收尾）：**
1. `P0b-01` 首页 4 卡片联调验收 — 当前最主要收尾项
2. 非功能性验证 — 扫描性能 / 数据稳定性 / 结果正确性抽查
3. `P0b-06` 形态筛选条件集成 — Phase 0b 剩余明确功能项

**然后进入 Phase 1：**
4. `P1-01` 筛选条件 → 策略打通 — Phase 1 的起手式
5. `P1-02` 回测报告完善
6. `P1-03` 策略对比

---

## 迭代自检

每轮开发前后问：
1. 这次是否让"扫描 → 筛选 → 验证"更顺了？
2. 结果是否更可信、更可解释了？
3. 是否只是让产品看起来更完整，而不是更好用？
4. 如果删掉这项工作，产品是否反而更聚焦？

---

## 最终判断标准

> **先把"扫描 → 筛选 → 验证"做到自己每天都想用，其他一切都是噪音。**
