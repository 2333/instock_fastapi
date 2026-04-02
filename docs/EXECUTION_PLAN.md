# InStock 执行计划（Execution Plan）

> 版本：v2.0 | 更新日期：2026-04-02
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
| 数据更新稳定性 | 连续 5 个交易日 100% | [-] 已有验证基座，待形成连续记录 |
| 扫描结果正确性 | 抽查 10 只命中股票，证据与实际数据一致 | [-] 已有验证基座，待形成抽查记录 |

#### 非功能验收记录（持续补充）

| 时间 | 范围 | 结果 | 备注 |
|------|------|------|------|
| 2026-04-02 05:58 CST | quick suite（screening baseline + task health + selection market services） | 通过（13/13） | 首次组合回归完成，三块非功能验收基座的首条正式记录已闭环 |
| 2026-04-02 06:30 CST | quick suite（screening baseline + task health + selection market services） | 通过（13/13） | 第二次组合回归完成，连续性记录开始形成 |
| 2026-04-02 07:02 CST | quick suite（screening baseline + task health + selection market services） | 通过（13/13） | 第三次组合回归完成，连续性记录进一步增强 |
| 2026-04-03 05:25 CST | quick suite（screening baseline + task health + selection market services） + 数据抓取 + Dashboard 端点验证 | 通过（13/13 + 数据就绪） | Dev 环境全链路验证完成，市场概览返回 5485 只股票真实数据，数据抓取任务成功执行 |

> 2026-04-02 heartbeat 备注：仓库内暂未发现现成的性能 / 压测 / 稳定性专项脚本或验收说明；当前“待验证”不是单纯还没执行，而是**验证资产本身尚未建立**。
>
> 最小验收方案草案（待执行）：
> 1. **扫描性能**：从仓库根目录准备一组固定筛选条件（例如 `priceMin + changeMin + macdBullish`），对主筛选接口连续执行 3 次，记录总耗时 / 返回数量 / trade_date，以最慢一次作为基线。
> 2. **数据更新稳定性**：基于 `market/task-health` 与 scheduler 相关表，连续抽查最近 5 个交易日的 latest trade_date 是否与基准交易日一致，并记录异常数据集。
> 3. **结果正确性**：从一次真实筛选结果中抽样 10 只股票，逐只比对返回 evidence 与 daily_bars / indicators / patterns 中的实际值是否一致。
> 已确认可复用基座：`tests/test_selection_market_services.py`（指标/筛选证据）、`tests/test_selection_schema.py`（结构化 reason/evidence）、`tests/test_selection_today_summary.py`（pattern 命中与摘要口径）、`tests/test_indicator_pattern_quality.py`（指标/形态计算质量）。下一步不是从零定义正确性，而是把这些自动化校验补成“10 只真实样本人工抽查记录”。
> 4. **输出物**：把验证过程、样本、结果和结论回写到 `docs/EXECUTION_PLAN.md` 或单独验收记录中，再决定是否通过门槛。
> 已确认可复用基座：`/api/v1/market/task-health`、`tests/test_api.py::TestMarketTaskHealthAPI`、`tests/test_scheduler.py`。下一步不是从零设计稳定性检查，而是把“单次健康判断”扩成“最近 5 个交易日连续记录”。

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
  - [x] 实际联调确认 4 张卡片在真实登录态/真实数据下展示稳定（2026-04-03 Dev 环境验证通过）
  - [x] 校正 Dashboard 文案与 PRD 验收描述，避免计划文档继续落后于代码
- **已验证**：
  - [x] `tests/test_market_summary.py` 已覆盖 `GET /api/v1/market/summary`
  - [x] `tests/test_selection_today_summary.py` 已覆盖 `GET /api/v1/selection/today-summary`
  - [x] `web/src/views/Dashboard.vue` 已直接消费 `marketApi.getSummary()`、`selectionApi.getTodaySummary()`、`backtestApi.getBacktestHistory()`、`attentionApi.getList()`
- **当前缺口**：
  - [ ] 缺少前端工作台级联调 / E2E 验收入口；当前验证主要停留在 API 和静态代码接线层
  - [ ] `web/package.json` 当前仅提供 `dev / build / typecheck / lint / preview`，未发现 Playwright / Cypress / Vitest 等前端联调测试资产
- **当前判断**：
  - [x] 本地手工联调路径具备基础前提：后端 `.env` 已提供本地数据库/API 运行配置，前端无额外 `.env` 依赖
  - [x] 本地运行环境已具备最小条件：后端 `.venv` 可用，前端 `node_modules` / `package-lock.json` / `npm` 均已就绪
  - [x] 因此 Dashboard 收尾更适合优先走“手工联调记录”而不是先补测试框架
- **下一步动作**：
  - [ ] 直接执行后端 `make dev` 与前端 `make frontend-dev`，完成一次 Dashboard 手工联调并记录结果
  - [x] 当前已确认服务尚未拉起：API `:8000` / Web `:5173` 均未监听；当前阻塞已收敛为唯一动作——启动服务
  - [x] 已确认推荐启动命令：后端 `make dev`，前端 `make frontend-dev`
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

#### P0b-06：形态筛选条件集成 [-]
- **文件**：`app/schemas/selection_schema.py`, `app/services/selection_service.py`, `web/src/views/Selection.vue`
- **现状**：单形态筛选链路已打通，前端已提供形态下拉，后端 schema / metadata / SQL 筛选 / 命中证据已支持 `pattern`
- **已完成**：
  - [x] 在筛选条件中支持单形态过滤（如 `HAMMER`、`HEAD_SHOULDERS`、`DOUBLE_BOTTOM`）
  - [x] 前端筛选面板已增加形态条件选项
  - [x] 今日摘要中已返回保存条件里的 `pattern`
- **待做**：
  - [ ] 评估是否需要支持多形态组合、形态分组或更细的 pattern_service 结果映射
  - [ ] 补充更贴近 PRD 文案的端到端验收说明（如“MACD 金叉 + 头肩底”组合演示）
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
后端策略模板和回测报告结构已成型，前端回测页的 URL 化、结果对比和历史回放也已接通。`Strategy.params` 的 canonical envelope 已统一完成，Phase 1 当前的主风险已转向“筛选策略进入回测的最终用户路径”和“回测结果结构化展示是否足够完整、可信、易解释”。

### 任务清单

#### P1-00：统一 Strategy.params 契约 [x]
- **文件**：`app/services/strategy_service.py`, `app/api/routers/strategy_router.py`, `app/schemas/strategy_schema.py`, `web/src/views/Backtest.vue`, `web/src/views/Selection.vue`
- **背景**：当前 `Strategy.params` 同时存在两种形态
  - 筛选桥接：`selection_filters / selection_scope / entry_rules / exit_rules`
  - 回测保存：`strategy_type / stock_code / period / initial_capital / ... / strategy_params`
- **已完成**：
  - [x] 定义唯一 canonical envelope，统一 `source / template_name / selection_filters / selection_scope / entry_rules / exit_rules / backtest_config / strategy_params`
  - [x] `/strategies/my` 与 `/strategies/my/from-selection` 写入同一结构
  - [x] Backtest 页可继续兼容旧数据，后端写入已统一
  - [x] 移除标准化输出与前端保存里的 legacy 顶层扁平镜像字段，仅保留 `backtest_config` 作为回测配置承载
  - [x] 补测试覆盖：selection payload、manual backtest payload、旧 payload 兼容读取
- **验收**：同一套 `Strategy.params` 既能表达筛选桥接策略，也能表达回测保存策略，前后端不再靠分叉字段名硬兼容

#### P1-01：筛选条件 → 策略模板打通 [x]
- **文件**：`app/services/strategy_service.py`, `app/api/routers/strategy_router.py`, `web/src/views/Selection.vue`, `web/src/views/Backtest.vue`
- **现状**：筛选页已支持一键“保存为策略 / 保存并去回测”，后端已提供 `selection_bridge` 模板与 `/strategies/my/from-selection`，Backtest 页已可承接 selection-derived strategy 的桥接上下文
- **已完成**：
  - [x] 用户在筛选页可一键"将当前条件保存为策略"
  - [x] 策略模板可直接暴露筛选条件 schema 元信息
  - [x] 入场条件 = 筛选条件、出场条件 = 可配置 的桥接结构已落地
  - [x] Selection 页已支持“保存并去回测”，可携带当前 Top1 命中股票进入 Backtest
  - [x] Backtest 页已可识别并导入 selection-derived strategy 的桥接上下文，并在同页继续补股票/模板后运行
- **验收**：在筛选页保存一组条件 → 在策略/回测体系内看到对应策略 → 后续可平滑进入回测

#### P1-02：回测报告结构化 [-]
- **文件**：`app/services/backtest_service.py`, `app/schemas/`
- **现状**：基础结构化报告已落地，包含 performance / benchmark / risk / equity_curve / trades，且已覆盖兼容旧 payload 的回退逻辑
- **已完成**：
  - [x] 输出 schema 化 JSON 结构（`BacktestReport` / `BacktestBenchmarkSummary` / `BacktestRiskSummary`）
  - [x] 报告包含：收益曲线、最大回撤、胜率、盈亏比、年化收益率
  - [x] 风险摘要包含：最大连续亏损天数、最大单日损失、风险等级、风险说明
  - [x] 已有测试覆盖：`tests/test_backtest_report_structure.py`
- **待做**：
  - [ ] 将代理基准升级为真实指数基准（沪深 300 / 上证指数）
  - [ ] 继续完善前端回测结果页的结构化展示与解释文案
- **验收**：回测结果页展示完整的报告，数据可信且可解释

#### P1-03：策略参数对比 [-]
- **文件**：`web/src/views/Backtest.vue`
- **现状**：结果对比表、核心指标 delta、收益曲线叠加图、对照基线选择器都已接通；URL 状态刷新恢复也已落地
- **已完成**：
  - [x] 同一策略不同参数版本的回测结果并排对比
  - [x] 核心指标对比表：收益率、回撤、胜率、夏普比率
  - [x] 收益曲线叠加图
- **待做**：
  - [ ] 统一“对比对象”的参数来源契约，避免历史快照和已保存策略双轨并存
  - [ ] 补更完整的参数 diff 展示，而不是仅展示当前模板前几个参数
- **验收**：用户跑两次不同参数的回测 → 在对比页看到差异

#### P1-04：回测任务异步化 [ ]
- **文件**：`app/api/routers/backtest_router.py`, `app/services/backtest_service.py`
- **待做**：
  - [ ] 回测作为后台任务运行（大时间跨度回测可能耗时较长）
  - [ ] 前端轮询或 SSE 获取进度
  - [ ] 回测任务状态持久化（pending → running → completed / failed）
- **验收**：发起跨 1 年回测 → 前端显示进度 → 完成后自动刷新结果

#### P1-05：策略保存与 URL 化 [-]
- **文件**：`app/api/routers/strategy_router.py`
- **现状**：Backtest 页已支持 `stock / period / strategy / saved / bt / cbt` 与关键参数 URL 化，刷新可恢复；浏览器 query 变更也已开始回流到页面状态
- **已完成**：
  - [x] 策略 + 参数 + 回测结果可通过 URL 复现
  - [x] 前端 URL 即状态（刷新不丢失上下文）
- **待做**：
  - [ ] 把 URL 化能力和统一 `Strategy.params` 契约对齐
  - [ ] 补前端联调 / E2E 资产，验证分享链接在真实交互下稳定
- **验收**：复制回测结果页 URL → 新标签页打开 → 完整复现

---

## Phase 1.5：数据层改造

> 决策日期：2026-04-02
> 完整技术方案：[DATA_LAYER_REPORT.md](./DATA_LAYER_REPORT.md)

### 前置条件
- **Phase 0b DoD 已通过**（首页联调、非功能性验证、形态筛选）
- **Phase 1 核心项已完成**（P1-02 回测基准、P1-03 参数对比、P1-04 异步回测）
- 当前"扫描 → 筛选 → 验证"主线稳定运行

### 为什么不能提前

| 风险 | 说明 |
|------|------|
| `fund_flows` → `moneyflow` 表替换 | Dashboard Card 1 依赖资金流数据，改表会直接打断 Phase 0b 联调验收 |
| `stock_tops` → `top_list` 替换 | `market_data_service.get_lhb()` 需重写，影响 Dashboard |
| `fetch_daily_task` 重构 | 日线获取是全系统基础，改动后"连续10个交易日稳定"的验证窗口被重置 |
| Alembic 引入 | 需与现有 `init_db()` auto-create 逻辑对接，时机不对会打断开发节奏 |

### 目标
统一数据源管理、补全数据维度、建立数据质量体系，为 Phase 2 体验打磨和未来功能扩展（基本面筛选、筹码分析、技术因子对比）提供数据基础。

### 改造范围概要

**改造现有表：**
- `stocks` 补全字段：fullname, cnspell, is_hs, act_name, asset_type 等（对齐 `stock_basic` 全字段）
- `fund_flows` → `moneyflow`：大单/中单/小单/超大单买卖明细替代现有汇总值
- `stock_tops` → `top_list`：对齐 Tushare `top_list` 全字段
- `daily_bars` 统一走 `pro_bar` 通用行情接口，支持 asset=E/I/FT/O/FD

**新增 6 张表：**

| 表名 | Tushare 接口 | 用途 |
|------|-------------|------|
| `daily_basic` | `daily_basic` | 每日指标：换手率、PE/PB/PS、总市值、流通市值 |
| `stock_st` | `stock_st` | ST 股票列表快照 |
| `broker_forecast` | `report_rc` | 券商盈利预测 |
| `chip_performance` | `cyq_perf` | 每日筹码成本与胜率 |
| `chip_distribution` | `cyq_chips` | 每日筹码分布 |
| `technical_factors` | `stk_factor_pro` | 210+ 技术面因子 |

### 执行工作流（4 条并行线）

```
WS-0 基础设施 (2d)  ──→  WS-1 核心改造 (3d)  ──→  WS-4 服务接入 (3d)
                    ──→  WS-2 新接口接入 (4d) ──→
                    ──→  WS-3 质量保障 (2d)   ──→
```

- **WS-0**：Alembic 迁移框架 + 通用行情抽象 (`pro_bar`) + 数据质量框架 + 积分检测
- **WS-1**：stocks 补全 + moneyflow 替换 + top_list 替换 + pro_bar 统一行情 + 指数入库
- **WS-2**：6 个新接口各自独立（**最高并行度，6 任务全并行**）
- **WS-3**：完整性检查 + 范围校验 + 跨源一致性 + 告警 + 回填工具
- **WS-4**：Repository + API 端点 + 筛选条件集成 (PE/PB/换手率/市值) + ST 过滤 + 筹码可视化

详细任务分解和字段定义见 [DATA_LAYER_REPORT.md](./DATA_LAYER_REPORT.md)。

### 验收标准
- [ ] 10 个 Tushare 接口已对接并可自动调度
- [ ] 每个新表有 Model + Migration + Fetch Task + Unit Test
- [ ] stocks 表包含 `stock_basic` 全字段
- [ ] moneyflow 表包含大单/中单/小单/超大单买卖明细
- [ ] 通用行情接口支持 asset=E/I 获取
- [ ] 数据质量检查覆盖：完整性 + 范围 + 跨源一致性
- [ ] 历史数据回填工具可按日期范围运行
- [ ] 新数据通过 API 端点可访问
- [ ] 筛选引擎支持 PE/PB/换手率/市值等基本面条件
- [ ] ST 股票可在筛选中被过滤

### 可提前做的零风险准备（与 Phase 0b/1 并行）

以下任务不触碰现有表结构和获取逻辑，可安全并行：

- [ ] **积分检测脚本** `scripts/check_tushare_points.py` — 确认当前可用接口范围
- [ ] **新表 Model 定义** — 只写 Python class，不执行 create table
- [ ] **Tushare Provider 新方法骨架** — `fetch_daily_basic()`, `fetch_moneyflow()` 等，不接入调度
- [ ] **数据质量框架骨架** `core/quality/validator.py` — 纯新增文件

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
- [-] 选股引擎端到端测试（真实条件 → 真实结果 → 验证证据正确性）
  - 已新增最小基线：`tests/test_screening_baseline.py`，对 `/api/v1/screening/run` 连续执行 3 次并记录耗时 / 返回数量 / trade_date 一致性
- [ ] 回测报告结构测试
- [ ] 前端 E2E 测试（至少覆盖扫描 → 结果 → 详情主线）

---

## 暂不进入执行

| 事项 | 原因 |
|------|------|
| Parquet 每日导出 | 等 Phase 1 回测有性能瓶颈时再做 |
| DuckDB 迁移 | 同上 |
| AI 助手 | Phase 1.5 数据层稳定后再接入 |
| 低代码策略编排器 | Phase 2+ |
| 移动端适配 | Phase 2+ |
| 多市场扩张 | 不在当前规划 |
| 期货/期权数据接入 | Phase 1.5 先覆盖 E(股票)+I(指数)，FT/O 留到有明确需求时 |

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
   - 执行入口已确认：可复用 `tests/conftest.py` 的 ASGI client 与现有 router 测试夹具，先补一个最小筛选接口基线测试/脚本，再记录结果
   - 建议固定 quick suite：`pytest tests/test_screening_baseline.py tests/test_api.py::TestMarketTaskHealthAPI tests/test_selection_market_services.py -q`，覆盖三块非功能验收基座的快速回归
3. `P0b-06` 形态筛选条件集成 — Phase 0b 剩余明确功能项

**可安全并行（Phase 1.5 零风险准备）：**
- 积分检测脚本、新表 Model 定义、Tushare Provider 新方法骨架、数据质量框架骨架
- 这些不触碰现有表结构和获取逻辑，详见 Phase 1.5 章节

**然后进入 Phase 1：**
4. `P1-02` 回测报告完善 — 真实指数基准
5. `P1-03` 策略对比 — 参数来源契约统一
6. `P1-04` 异步回测 — 长跨度回测后台化

**Phase 1 DoD 通过后进入 Phase 1.5：**
7. 数据层改造 — 统一行情、补全字段、新接口接入、质量体系（详见 Phase 1.5 章节）

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
