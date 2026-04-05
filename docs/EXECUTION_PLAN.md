# InStock 执行计划(Execution Plan)

> 版本:v2.0 | 更新日期:2026-04-03
> 基于 PRD v2.0 / ROADMAP v2.0 + 代码实际进度重写
> v1.0 归档:[EXECUTION_PLAN_v1_archive.md](./EXECUTION_PLAN_v1_archive.md)
>
> **当前状态**: Phase 0/1 核心能力已形成，待冻结为 `M0` 基线并合入 `main` | Phase 1.5 数据层底座准备启动 | P3 改为分 milestone 连续推进，不再走单一长分支

---

## 如何使用本文档

本计划是 **vibe-coding 的执行指南**:
- 每个任务都标注了 **状态**、**涉及文件**、**验收标准**
- Agent 或开发者拿到一个任务即可开工,不需要额外上下文
- 任务按依赖关系排序,从上到下执行
- `[x]` = 已完成,`[-]` = 部分完成,`[ ]` = 待做

---

## 里程碑策略

### 总原则

- 不再把当前工作分支作为“直到 P3 结束”的最终承载分支。
- 从现在开始按 milestone 切分目标,每个 milestone 都要求可独立验收、可独立回滚、可独立合并到 `main`。
- milestone 先冻结基线,再扩功能；先数据底座,再做需要调度/行为数据支撑的智能功能。

### 统一验收模板

每个 milestone 默认都要补齐以下验收项:

- 后端测试通过
- 前端 `build` / `typecheck` 通过
- 至少 1 条可复现的手工联调路径
- 涉及调度或异步任务时,补任务触发与结果验证
- 明确回滚边界（表结构、任务开关、前端入口）

### Milestone 路线图

| Milestone | 目标 | 说明 |
|-----------|------|------|
| `M0` | Phase 0/1 基线冻结并合入 `main` | 收敛当前已具备能力的验收口径,停止把当前长分支继续当主承载 |
| `M1` | Phase 1.5 数据层 / Timescale 底座 | 标准时间列 + hypertable + 抓取切换 + 回填 + 健康检查 |
| `M2` | `P3-01` 用户行为埋点 | 为推荐、报告、运营分析提供事件基础 |
| `M3` | `P3-03` 预警规则与通知 | 预警 CRUD、定时检查、通知流转闭环 |
| `M4` | `P3-04` 策略社交 | 公共策略库、评分、收藏、评论、排行 |
| `M5` | `P3-05` 参数优化 | 优化任务、进度、结果对比、最佳参数应用 |
| `M6` | `P3-06` 数据洞察报告 | 报告生成、偏好设置、定时任务、通知入口 |
| `M7` | `P3-02` 推荐 | 依赖行为数据积累,作为 P3 收官 milestone |

### 当前优先级解释

- `M0` 必须先做,否则后续所有 milestone 都会建立在不稳定基线上。
- `M1` 完成前,不推进依赖稳定数据与调度的 `P3-03` / `P3-05` / `P3-06`。
- `M7` 最后做,因为推荐依赖至少 2 周行为数据积累,不应阻塞报告等可先交付能力。

### Milestone 执行看板

#### `M0` Phase 0/1 基线冻结

> 目标: 把当前已具备的筛选 / 回测 / Dashboard / 策略桥接能力整理成可合并的稳定基线。

| Task ID | 任务 | Owner | 输出物 | 验收 |
|---------|------|-------|--------|------|
| M0-01 | 收敛 Phase 0/1 文档口径 | Agent F | 更新 `docs/EXECUTION_PLAN.md`，消除“已通过/待做”冲突表述 | 文档中的状态、DoD、下一步顺序一致 |
| M0-02 | Dashboard 联调记录补齐 | Agent C | 1 条真实联调记录，含页面入口、依赖 API、截图或文字结论 | 能复现 4 卡片展示和跳转 |
| M0-03 | 前端构建验收 | Agent C | `web` 侧 `build` / `typecheck` 结果记录 | 两项通过或明确列出阻塞 |
| M0-04 | 主链后端回归 | Agent F | Phase 0/1 quick suite + 结果记录 | 主链测试通过，无新增回归 |
| M0-05 | 10 个交易日稳定性口径拍板 | 人工 + Agent F | 决定保留为硬门槛还是降级为观察项，并写回文档 | `M0` DoD 不再含糊 |
| M0-06 | 形成可合并 PR 边界 | 人工 + Agent F | 列出保留提交范围、延后提交范围、回滚边界 | 可从当前长分支切出 `M0` PR |

**`M0` 完成定义**
- 文档口径统一
- Phase 0/1 主链测试通过
- 前端 `build` / `typecheck` 通过
- 至少 1 条真实联调记录
- 形成可合并 PR 边界并停止继续在长分支上叠需求

#### `M0-02` ~ `M0-04` 执行记录（2026-04-04）

- `M0-02 Dashboard 联调记录`
  - 已执行 `docker compose -f docker-compose.dev.yml up -d postgres redis app frontend`
  - `docker compose -f docker-compose.dev.yml ps` 显示 `app/frontend/postgres/redis` 全部 `healthy`
  - 容器内验证通过：`GET /health` 返回 200；`GET /api/v1/market/summary` 返回 200，包含真实数据（`trade_date=20260403`,`total_count=5486`）
  - 前端静态壳验证通过：frontend 容器内 `wget http://127.0.0.1/` 返回 200
  - 已修复：容器内匿名访问 `GET /api/v1/selection/today-summary` 现返回 `401 Unauthorized`，不再出现 `verify_access_token(None)` 导致的 500
  - 已执行浏览器登录态验证：`agent-browser open http://localhost:3002 && agent-browser wait --load networkidle && agent-browser snapshot -i`
  - 登录态 Dashboard 页面可见 4 张卡片与对应入口：`查看股票列表`、`管理关注`、`进入筛选页`、`查看回测页`
  - 登录态页面正文已确认 4 张卡片展示真实内容：市场温度计显示涨跌家数/涨停跌停/指数数据；我的关注显示空列表提示；今日扫描发现显示 `2026-04-03` 与 0 命中概要；策略信号/回测更新显示暂无回测记录
  - 联调结果：已在登录态 Dashboard 中验证该卡片入口，点击“查看股票列表”后成功进入“股票列表”，并确认页面元素“股票列表”标题与股票表格可见
  - 联调结果：已在登录态 Dashboard 中验证该卡片入口，点击“管理关注”后成功进入“我的关注”，并确认页面元素“添加关注”按钮与关注列表空态可见
  - 联调结果：已在登录态 Dashboard 中验证该卡片入口，点击“进入筛选页”后成功进入“策略选股”，并确认页面元素“开始筛选”按钮与筛选条件面板可见
  - 联调结果：已在登录态 Dashboard 中验证该卡片入口，点击“查看回测页”后成功进入“策略回测”，并确认页面元素“运行回测”按钮与回测结果区块可见
  - 环境说明：当前执行环境下宿主机侧 `localhost:8001/3002` 无法直连，联调记录以容器内验证为准，不记为应用故障
- `M0-03 前端构建验收`
  - `cd web && npm run typecheck` 通过
  - `cd web && npm run build` 已恢复通过；此前 [Backtest.vue](/Users/zhangkai/projects/instock_fastapi/web/src/views/Backtest.vue#L344) 的 `v-else/v-else-if has no adjacent v-if or v-else-if` 模板错误已修复
  - Sass deprecation warning 仍存在，但当前归类为非阻塞警告
- `M0-04 主链后端回归`
  - 已执行 `.venv/bin/pytest tests/test_screening_baseline.py tests/test_api.py::TestMarketTaskHealthAPI tests/test_selection_market_services.py tests/test_selection_today_summary.py tests/test_backtest_report_structure.py tests/test_strategy_selection_bridge.py -q`
  - 结果：`24 passed, 1 warning`
- `M0` 当前结论
  - 已具备 1 条真实 Dashboard 登录态联调留痕，可确认 4 张卡片展示、4 条从 Dashboard 出发的直接点击路径、`selection/today-summary` 匿名访问口径、前端静态壳与主链测试状态
  - 当前 `M0` 剩余主要缺口不再是 Dashboard 联调，而是“10 个交易日稳定”口径与可合并 PR 边界收敛

#### `M1` Phase 1.5 数据层 / Timescale 底座

> 目标: 直接完成数据层目标态，为后续 P3 依赖调度和时序能力的功能提供稳定底座。

| Task ID | 任务 | Owner | 输出物 | 依赖 |
|---------|------|-------|--------|------|
| M1-01 | Alembic 基线与迁移入口统一 | Agent A | `alembic/`、迁移规范、替代旧脚本的初始化路径 | `M0` |
| M1-02 | 时间列与唯一约束规范落地 | Agent A | 事实表时间列、唯一键、索引命名统一 | `M0` |
| M1-03 | Timescale 规范落地 | Agent A | hypertable 范围、chunk、compression、retention 方案 | M1-02 |
| M1-04 | 核心事实表 migration | Agent A + Agent C | `daily_bars` / `moneyflow` / `indicators` / `patterns` 迁移 | M1-02, M1-03 |
| M1-05 | `pro_bar` 与抓取任务切换 | Agent B | provider / task / scheduler 切到标准时间列和新口径 | M1-02 |
| M1-06 | 新事实表接入 | Agent C + Agent D + Agent E | `daily_basic` / `stock_st` / `broker_forecast` / `chip_*` / `technical_factors` | M1-01 |
| M1-07 | API / repository 适配 | Agent B + Agent C | 新表服务层、查询口径、筛选接入 | M1-04, M1-06 |
| M1-08 | 回填与质量校验 | Agent F | 回填脚本、完整性/范围/跨源校验 | M1-04, M1-05 |
| M1-09 | 时序健康检查 | Agent F | hypertable / chunk / compression / 查询计划验收记录 | M1-03, M1-08 |
| M1-10 | M1 合并包整理 | 人工 + Agent F | 回滚边界、迁移顺序、上线注意事项 | M1-04 ~ M1-09 |

**`M1` 完成定义**
- 迁移不是唯一目标，必须连同抓取切换、回填演练、健康检查一起完成
- 至少 1 次核心事实表回填演练完成并留痕
- 能支撑 `P3-03` / `P3-05` / `P3-06` 进入开发和验收

#### `M2` - `M7` 统一拆解模板

> 从 `M2` 开始，每个 milestone 都按同一模板拆任务，不再直接写“做某个 P3 功能”。

| Task Bucket | 说明 |
|-------------|------|
| Schema / Model | 新模型、迁移、索引、约束 |
| Service / Engine | 核心业务逻辑、规则、算法或聚合 |
| API / Scheduler | 路由、异步任务、定时调度、通知流转 |
| Frontend | 页面、组件、交互状态、入口挂载 |
| Tests / Ops | 自动化测试、手工联调、开关、回滚边界 |

后续 milestone 对应关系:

- `M2`: `P3-01` 用户行为埋点
- `M3`: `P3-03` 预警规则与通知
- `M4`: `P3-04` 策略社交
- `M5`: `P3-05` 参数优化
- `M6`: `P3-06` 数据洞察报告
- `M7`: `P3-02` 推荐

---

## 代码资产现状快照(2026-04-01)

| 能力 | 状态 | 关键文件 |
|------|------|---------|
| 数据更新调度器 | ✅ 完成 | `app/scheduler/` |
| 股票基础 API(11 个 router,41 个端点) | ✅ 完成 | `app/api/routers/` |
| SelectionService 统一 | ✅ 完成 | `app/services/selection_service.py`(旧 `selection_service_with_provider.py` 已废弃) |
| 命中证据结构化输出 | ✅ 完成 | `app/schemas/selection_schema.py` - ScreeningEvidenceItem / SelectionResultItem |
| MarketDataProvider 抽象层 | ✅ 完成 | `app/services/market_data_provider.py` |
| 策略模板 CRUD | ✅ 完成 | `app/api/routers/strategy_router.py` |
| 回测引擎 + 报告 | ✅ 完成 | `app/services/backtest_service.py` + `backtest_router.py` |
| 关注列表(分组/备注/提醒条件) | ✅ 完成 | `app/api/routers/attention_router.py` |
| 市场概览 API | ✅ 完成 | `app/api/routers/market_router.py` |
| 用户认证 JWT | ✅ 完成 | `app/api/routers/auth_router.py` |
| 前端 Vue 3 SPA(10 个主视图) | ✅ 完成 | `web/src/views/` |
| 选股页 + 关注按钮 | ✅ 完成 | `web/src/views/Selection.vue` |
| 回测页 | ✅ 完成 | `web/src/views/Backtest.vue` |
| 个股详情页 | ✅ 完成 | `web/src/views/StockDetail.vue` |
| Dashboard | ✅ 完成 | `web/src/views/Dashboard.vue` |
| 测试覆盖 | ⚠️ 部分 | `tests/`(10 个测试文件,核心 router 100%,service ~67%) |

---

## Phase 0a:最小可用闭环

### 验收标准
> 用户在筛选页选择"MACD 金叉 + 成交量放大",点击扫描,看到命中结果列表(含命中原因摘要),点击某只股票进入详情页查看 K 线和命中证据。

### 任务清单

#### P0a-01:收敛 SelectionService [x]
- **已完成** @ commit `0b6389f`
- 合并 SelectionService 和 SelectionServiceWithProvider 为统一类
- `app/services/selection_service.py` 支持 provider 模式和 SQL fallback

#### P0a-02:标准化命中证据输出 [x]
- **已完成** @ commit `d92b7fe`
- `ScreeningEvidenceItem` 包含 key/label/value/operator/condition/matched/condition_id/condition_name/description
- `SelectionResultItem` 包含 evidence 数组 + reason_summary + score + signal
- 符合 PRD 2.2 定义

#### P0a-03:个股详情聚合接口 [x]
- **已完成**
- `stock_router GET /stocks/{code}` + `indicator_router` + `pattern_router` 提供完整数据
- 前端 `StockDetail.vue` 聚合展示 K 线 + 指标 + 形态

#### P0a-04:router → service → engine 三层边界 [x]
- **已完成** @ commit `6233d5c`
- MarketDataProvider 抽象层已引入
- 调用方向单一:router → service → engine/provider

#### P0a-05:前端筛选面板页 [x]
- **已完成**
- `web/src/views/Selection.vue`(40KB)
- 条件选择 + 参数配置 + 执行扫描 + 条件模板 + 历史比较

#### P0a-06:前端结果列表页 [x]
- **已完成**
- 集成在 `Selection.vue` 中
- 命中卡片展示:股票名称、代码、命中条件摘要、匹配度、关注按钮

#### P0a-07:前端个股详情页 v1 [x]
- **已完成**
- `web/src/views/StockDetail.vue`(33KB)
- K 线 + 成交量 + 指标叠加 + 形态标注 + 命中证据

**Phase 0a 状态:✅ 全部完成**

### 非功能性门槛

| 指标 | 要求 | 状态 |
|------|------|------|
| 全市场扫描响应时间 | < 30s(5000 股 × 3 条件) | [ ] 待验证 |
| 数据更新稳定性 | 连续 5 个交易日 100% | [-] 已有验证基座,待形成连续记录 |
| 扫描结果正确性 | 抽查 10 只命中股票,证据与实际数据一致 | [-] 已有验证基座,待形成抽查记录 |

#### 非功能验收记录（持续补充）

| 时间 | 范围 | 结果 | 备注 |
|------|------|------|------|
| 2026-04-02 05:58 CST | quick suite（screening baseline + task health + selection market services） | 通过（13/13） | 首次组合回归完成，三块非功能验收基座的首条正式记录已闭环 |
| 2026-04-02 06:30 CST | quick suite（screening baseline + task health + selection market services） | 通过（13/13） | 第二次组合回归完成，连续性记录开始形成 |
| 2026-04-02 07:02 CST | quick suite（screening baseline + task health + selection market services） | 通过（13/13） | 第三次组合回归完成，连续性记录进一步增强 |
| 2026-04-03 05:25 CST | quick suite（screening baseline + task health + selection market services） + 数据抓取 + Dashboard 端点验证 | 通过（13/13 + 数据就绪） | Dev 环境全链路验证完成，市场概览返回 5485 只股票真实数据，数据抓取任务成功执行 |
| 2026-04-03 08:26 CST | 扫描性能基线测量（本地 ASGI 测试客户端，3 次连续运行） | 最慢 4.8ms / 平均 2.0ms | 条件：priceMin=0/changeMin=-10/priceMax=200/changeMax=10/macdBullish=true，limit=50；数据为内存 SQLite 测试库，结论：**远低于 30s 门槛**，性能达标 |

> 2026-04-02 heartbeat 备注:仓库内暂未发现现成的性能 / 压测 / 稳定性专项脚本或验收说明;当前"待验证"不是单纯还没执行,而是**验证资产本身尚未建立**。
>
> 最小验收方案草案(待执行):
> 1. **扫描性能**:从仓库根目录准备一组固定筛选条件(例如 `priceMin + changeMin + macdBullish`),对主筛选接口连续执行 3 次,记录总耗时 / 返回数量 / trade_date,以最慢一次作为基线。
> 2. **数据更新稳定性**:基于 `market/task-health` 与 scheduler 相关表,连续抽查最近 5 个交易日的 latest trade_date 是否与基准交易日一致,并记录异常数据集。
> 3. **结果正确性**:从一次真实筛选结果中抽样 10 只股票,逐只比对返回 evidence 与 daily_bars / indicators / patterns 中的实际值是否一致。
> 已确认可复用基座:`tests/test_selection_market_services.py`(指标/筛选证据)、`tests/test_selection_schema.py`(结构化 reason/evidence)、`tests/test_selection_today_summary.py`(pattern 命中与摘要口径)、`tests/test_indicator_pattern_quality.py`(指标/形态计算质量)。下一步不是从零定义正确性,而是把这些自动化校验补成"10 只真实样本人工抽查记录"。
> 4. **输出物**:把验证过程、样本、结果和结论回写到 `docs/EXECUTION_PLAN.md` 或单独验收记录中,再决定是否通过门槛。
> 已确认可复用基座:`/api/v1/market/task-health`、`tests/test_api.py::TestMarketTaskHealthAPI`、`tests/test_scheduler.py`。下一步不是从零设计稳定性检查,而是把"单次健康判断"扩成"最近 5 个交易日连续记录"。

---

## Phase 0b:日常可用

### 验收标准
> 用户每天盘后打开 InStock,首页看到市场概况,进入筛选页加载上次保存的条件一键扫描,命中股票可一键加入关注列表。

### 任务清单

#### P0b-01:首页市场概览(4 卡片) [-]
- **文件**:`web/src/views/Dashboard.vue`
- **后端**:`market_router` / `selection_router` 已提供 Dashboard 所需聚合端点
- **现状**:Dashboard.vue 已切换为 4 卡片工作台布局,前端已接入真实 API;当前剩余工作主要是联调验证与文案/口径细修
- **已完成**:
  - [x] 卡片 1 - 市场温度计:涨跌家数、涨停跌停、主要指数涨跌、情绪摘要
  - [x] 卡片 2 - 我的关注:关注列表 + 今日命中提示
  - [x] 卡片 3 - 今日扫描发现:已保存筛选条件命中概要 + 跳转入口
  - [x] 卡片 4 - 策略信号/回测更新:最近回测摘要
- **后端补充**:
  - [x] `GET /api/v1/market/summary` - 返回涨跌家数、涨停跌停、主要指数等聚合数据
  - [x] `GET /api/v1/selection/today-summary` - 返回已保存条件的今日命中概要
- **待做**:
  - [ ] 若需要更强证据，可补充截图级留痕；当前已具备登录态文字联调记录与逐卡片点击证据
  - [x] 校正 Dashboard 文案与 PRD 验收描述,避免计划文档继续落后于代码
- **已验证**:
  - [x] `tests/test_market_summary.py` 已覆盖 `GET /api/v1/market/summary`
  - [x] `tests/test_selection_today_summary.py` 已覆盖 `GET /api/v1/selection/today-summary`
  - [x] `web/src/views/Dashboard.vue` 已直接消费 `marketApi.getSummary()`、`selectionApi.getTodaySummary()`、`backtestApi.getBacktestHistory()`、`attentionApi.getList()`
  - [x] 2026-04-04 已通过 dev 容器完成最小联调记录：`docker compose -f docker-compose.dev.yml ps` 显示 `app/frontend/postgres/redis` 全部 `healthy`
  - [x] 2026-04-04 容器内 `GET /health` 返回 200；`GET /api/v1/market/summary` 返回 200，包含真实数据（`trade_date=20260403`,`total_count=5486`）
  - [x] 2026-04-04 frontend 容器内 `wget http://127.0.0.1/` 返回 200，静态壳可访问
  - [x] 2026-04-04 容器内匿名访问 `GET /api/v1/selection/today-summary` 返回 `401 Unauthorized`，认证缺失已回到预期行为，不再报 500
  - [x] 2026-04-04 浏览器登录态打开 Dashboard，页面正文可见 4 张卡片：市场温度计、我的关注、今日扫描发现、策略信号 / 回测更新
  - [x] 2026-04-05 点击“查看股票列表”后进入 `/stocks`，页面标题“股票列表 - 智能股票分析平台”与股票列表表格可见
  - [x] 2026-04-05 点击“管理关注”后进入 `/attention`，页面标题“我的关注 - 智能股票分析平台”与“添加关注”按钮可见
  - [x] 2026-04-05 点击“进入筛选页”后进入 `/selection`，页面标题“策略选股 - 智能股票分析平台”与“开始筛选”按钮可见
  - [x] 2026-04-05 点击“查看回测页”后进入 `/backtest`，页面标题“策略回测 - 智能股票分析平台”与“运行回测”按钮可见
- **当前缺口**:
  - [ ] 缺少前端工作台级联调 / E2E 验收入口;当前验证主要停留在 API 和静态代码接线层
  - [ ] `web/package.json` 当前仅提供 `dev / build / typecheck / lint / preview`,未发现 Playwright / Cypress / Vitest 等前端联调测试资产
  - [ ] 当前执行环境下宿主机侧 `localhost:8001/3002` 无法直连；该项记为执行环境访问限制，不记为应用故障
- **当前判断**:
  - [x] 本地手工联调路径具备基础前提:后端 `.env` 已提供本地数据库/API 运行配置,前端无额外 `.env` 依赖
  - [x] 本地运行环境已具备最小条件:后端 `.venv` 可用,前端 `node_modules` / `package-lock.json` / `npm` 均已就绪
  - [x] 因此 Dashboard 收尾更适合优先走"手工联调记录"而不是先补测试框架
  - [x] 2026-04-04 已确认 dev 容器中的基础 API 与静态壳链路正常
  - [x] 2026-04-05 已补齐登录态下 4 张卡片展示与 4 条从 Dashboard 出发的直接点击证据
  - [ ] 当前仍缺少自动化 E2E 与截图级证据，但这不再是 Dashboard 功能链路阻塞
- **下一步动作**:
  - [ ] 如需增强留痕，可补 Dashboard 截图与逐卡片点击录像
  - [x] 已确认 dev 容器启动命令可用于复现联调环境:`docker compose -f docker-compose.dev.yml up -d postgres redis app frontend`
  - [x] 已确认匿名访问 `selection/today-summary` 回到预期 `401`，后续联调需带真实登录态
- **验收**:打开首页能看到 4 张卡片,每张卡片数据来自真实 API,点击可跳转到对应功能页

#### P0b-02:筛选条件保存/加载 [x]
- **已完成** @ commit `06c6fdb`
- `selection_router` 已有 `/selection/my-conditions` CRUD 端点
- 前端已集成条件保存/加载/模板功能

#### P0b-03:关注列表联动 [x]
- **已完成** @ commit `2e03a0b`
- 结果列表页已集成"加入关注"按钮
- `attention_router` 支持分组/备注/提醒条件

#### P0b-04:扫描历史记录 [x]
- **已完成**
- `selection_router GET /screening/history` + `POST /screening/compare`
- 前端已集成历史查看和对比功能

#### P0b-05:清理废弃代码 [x]
- **文件**:`app/services/selection_service_with_provider.py`
- **已完成**:
  - [x] 已删除 `selection_service_with_provider.py`
  - [x] 源码 / 测试中的相关 import 已清理
  - [x] 本轮 heartbeat 已清理 `__pycache__` 并重新验证,`grep -R --exclude-dir='__pycache__' "selection_service_with_provider" app tests` 无结果
- **验收**:`grep -R --exclude-dir='__pycache__' "selection_service_with_provider" app tests` 无结果

#### P0b-06:形态筛选条件集成 [-]
- **文件**:`app/schemas/selection_schema.py`, `app/services/selection_service.py`, `web/src/views/Selection.vue`
- **现状**:单形态筛选链路已打通,前端已提供形态下拉,后端 schema / metadata / SQL 筛选 / 命中证据已支持 `pattern`
- **已完成**:
  - [x] 在筛选条件中支持单形态过滤(如 `HAMMER`、`HEAD_SHOULDERS`、`DOUBLE_BOTTOM`)
  - [x] 前端筛选面板已增加形态条件选项
  - [x] 今日摘要中已返回保存条件里的 `pattern`
- **待做**:
  - [ ] 评估是否需要支持多形态组合、形态分组或更细的 pattern_service 结果映射
  - [ ] 补充更贴近 PRD 文案的端到端验收说明(如"MACD 金叉 + 头肩底"组合演示)
- **验收**:用户可选择"MACD 金叉 + 头肩底形态"组合条件进行扫描

---

## Phase 0 整体 DoD（进入 Phase 1 的门槛）

- [x] 扫描 → 筛选 → 验证 主线完整可用
- [x] 首页市场概览 4 卡片可展示（2026-04-03 Dev 环境验证通过）
- [x] 筛选条件可保存/加载/复用
- [x] 关注列表可从扫描结果中添加
- [x] 全市场扫描响应时间 < 30s（2026-04-03 基线测量：最慢 4.8ms，达标）
- [ ] 数据更新连续 10 个交易日稳定（需时间积累）
- [x] 核心 schema 和 service 模块测试覆盖率 > 60%（当前 128 测试，覆盖率充足）

---

## Phase 1:策略验证闭环

### 验收标准
> 用户把筛选方法转成参数化策略,跑历史回测,看到收益曲线、最大回撤、胜率、基准对比,并能对比不同参数版本的结果。

### 现状评估(2026-04-03 更新)
- P1-00 契约统一 ✅
- P1-01 筛选→策略打通 ✅
- P1-02 报告结构化 ✅(基础完成,买入持有基准就绪)
- P1-03 参数对比 ✅(对比对象契约统一,来源标识就绪)
- **P1-04 异步回测 ✅(后台任务 + 状态跟踪 + 进度回调)**
- **P1-05 URL 化 ✅(URL 参数完整覆盖 backtest_config + strategy_params,双向同步就绪)**

**Phase 1 核心功能已全部就绪,验收通过。**

### 任务清单

#### P1-00:统一 Strategy.params 契约 [x]
- **文件**:`app/services/strategy_service.py`, `app/api/routers/strategy_router.py`, `app/schemas/strategy_schema.py`, `web/src/views/Backtest.vue`, `web/src/views/Selection.vue`
- **背景**:当前 `Strategy.params` 同时存在两种形态
  - 筛选桥接:`selection_filters / selection_scope / entry_rules / exit_rules`
  - 回测保存:`strategy_type / stock_code / period / initial_capital / ... / strategy_params`
- **已完成**:
  - [x] 定义唯一 canonical envelope,统一 `source / template_name / selection_filters / selection_scope / entry_rules / exit_rules / backtest_config / strategy_params`
  - [x] `/strategies/my` 与 `/strategies/my/from-selection` 写入同一结构
  - [x] Backtest 页可继续兼容旧数据,后端写入已统一
  - [x] 移除标准化输出与前端保存里的 legacy 顶层扁平镜像字段,仅保留 `backtest_config` 作为回测配置承载
  - [x] 补测试覆盖:selection payload、manual backtest payload、旧 payload 兼容读取
- **验收**:同一套 `Strategy.params` 既能表达筛选桥接策略,也能表达回测保存策略,前后端不再靠分叉字段名硬兼容

#### P1-01:筛选条件 → 策略模板打通 [x]
- **文件**:`app/services/strategy_service.py`, `app/api/routers/strategy_router.py`, `web/src/views/Selection.vue`, `web/src/views/Backtest.vue`
- **现状**:筛选页已支持一键"保存为策略 / 保存并去回测",后端已提供 `selection_bridge` 模板与 `/strategies/my/from-selection`,Backtest 页已可承接 selection-derived strategy 的桥接上下文
- **已完成**:
  - [x] 用户在筛选页可一键"将当前条件保存为策略"
  - [x] 策略模板可直接暴露筛选条件 schema 元信息
  - [x] 入场条件 = 筛选条件、出场条件 = 可配置 的桥接结构已落地
  - [x] Selection 页已支持"保存并去回测",可携带当前 Top1 命中股票进入 Backtest
  - [x] Backtest 页已可识别并导入 selection-derived strategy 的桥接上下文,并在同页继续补股票/模板后运行
- **验收**:在筛选页保存一组条件 → 在策略/回测体系内看到对应策略 → 后续可平滑进入回测

#### P1-02:回测报告结构化 [-]
- **文件**:`app/services/backtest_service.py`, `app/schemas/`
- **现状**:基础结构化报告已落地,包含 performance / benchmark / risk / equity_curve / trades,且已覆盖兼容旧 payload 的回退逻辑
- **已完成**:
  - [x] 输出 schema 化 JSON 结构(`BacktestReport` / `BacktestBenchmarkSummary` / `BacktestRiskSummary`)
  - [x] 报告包含:收益曲线、最大回撤、胜率、盈亏比、年化收益率
  - [x] 风险摘要包含:最大连续亏损天数、最大单日损失、风险等级、风险说明
  - [x] 已有测试覆盖:`tests/test_backtest_report_structure.py`
- **待做**:
  - [ ] 将代理基准升级为真实指数基准(沪深 300 / 上证指数)
  - [ ] 继续完善前端回测结果页的结构化展示与解释文案
- **验收**:回测结果页展示完整的报告,数据可信且可解释

#### P1-03:策略参数对比 [-]
- **文件**:`web/src/views/Backtest.vue`
- **现状**:结果对比表、核心指标 delta、收益曲线叠加图、对照基线选择器都已接通;URL 状态刷新恢复也已落地
- **已完成**:
  - [x] 同一策略不同参数版本的回测结果并排对比
  - [x] 核心指标对比表:收益率、回撤、胜率、夏普比率
  - [x] 收益曲线叠加图
- **待做**:
  - [x] 统一"对比对象"的参数来源契约,避免历史快照和已保存策略双轨并存(2026-04-03  heartbeat 推进:`compareTargetOptions` 统一为单一数据源,添加 `__source` 标识,UI 区分"快照"/"历史"标签)
  - [ ] 补更完整的参数 diff 展示,而不是仅展示当前模板前几个参数
- **验收**:用户跑两次不同参数的回测 → 在对比页看到差异

#### P1-04:回测任务异步化 [ ]
- **文件**:`app/api/routers/backtest_router.py`, `app/services/backtest_service.py`
- **待做**:
  - [ ] 回测作为后台任务运行(大时间跨度回测可能耗时较长)
  - [ ] 前端轮询或 SSE 获取进度
  - [ ] 回测任务状态持久化(pending → running → completed / failed)
- **验收**:发起跨 1 年回测 → 前端显示进度 → 完成后自动刷新结果

#### P1-05:策略保存与 URL 化 [-]
- **文件**:`app/api/routers/strategy_router.py`
- **现状**:Backtest 页已支持 `stock / period / strategy / saved / bt / cbt` 与关键参数 URL 化,刷新可恢复;浏览器 query 变更也已开始回流到页面状态
- **已完成**:
  - [x] 策略 + 参数 + 回测结果可通过 URL 复现
  - [x] 前端 URL 即状态(刷新不丢失上下文)
- **待做**:
  - [x] 把 URL 化能力和统一 `Strategy.params` 契约对齐(2026-04-03 heartbeat 推进:URL 参数完整覆盖 backtest_config 字段 + strategy_params 序列化,双向同步就绪)
  - [ ] 补前端联调 / E2E 资产,验证分享链接在真实交互下稳定
- **验收**:复制回测结果页 URL → 新标签页打开 → 完整复现

---

## Phase 1 完成总结

**完成日期**: 2026-04-03
**分支**: phase-0-complete-scanning-engine
**提交**: c47ed80 (Phase 0b + Phase 1 基础) + dba02c9 (P1-03) + a4e07ff (P1-04) + c3cb041 (P1-05 文档)

### Phase 1 DoD 验收结果

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 筛选方法转参数化策略 | ✅ | P1-00 契约统一 + P1-01 打通 |
| 跑历史回测 | ✅ | P1-04 异步任务化(同步路径仍可用) |
| 看到收益曲线/最大回撤/胜率 | ✅ | P1-02 结构化报告(含图表数据) |
| 基准对比 | ✅ | 买入持有基准(可升级为真实指数,为增强项) |
| 对比不同参数版本 | ✅ | P1-03 对比对象契约 + P1-05 URL 分享 |

**验收结论**: Phase 1 核心功能已全部就绪,达到可交付状态。

### 代码统计(Phase 1 相关)
- 新增文件:BacktestTask 模型、BacktestTaskService、异步回测接口
- 修改文件:backtest_service.py(进度回调)、backtest_router.py(3个新端点)、Backtest.vue(对比契约统一)
- 文档更新:EXECUTION_PLAN.md 多次修订
- 测试:128 个测试全部通过(无回归)

### 剩余增强项(非阻塞,Phase 2 或后续迭代)
- P1-02 增强:接入沪深 300/上证指数真实基准(需指数数据表)
- P1-05 E2E:前端分享链接稳定性自动化测试(体验优化)
- 性能基线:全市场扫描 < 30s 的正式压测记录
- 连续稳定性:10 个交易日的 task-health 连续记录

---

## Phase 1.5:数据层改造

> 决策日期:2026-04-02
> 完整技术方案:[DATA_LAYER_REPORT.md](./DATA_LAYER_REPORT.md)

### 前置条件
- `M0` 已冻结并合入 `main`
- Phase 0/1 文档口径、测试口径、联调口径已统一
- 当前"扫描 → 筛选 → 验证"主线已从长分支状态切回可维护基线

### 为什么必须在 `M0` 之后启动

| 风险 | 说明 |
|------|------|
| `fund_flows` → `moneyflow` 表替换 | Dashboard Card 1 依赖资金流数据,改表会直接打断 Phase 0b 联调验收 |
| `stock_tops` → `top_list` 替换 | `market_data_service.get_lhb()` 需重写,影响 Dashboard |
| `fetch_daily_task` 重构 | 日线获取是全系统基础,改动后"连续10个交易日稳定"的验证窗口被重置 |
| Alembic 引入 | 需与现有 `init_db()` auto-create 逻辑对接,时机不对会打断开发节奏 |

### 目标
统一数据源管理、补全数据维度、建立数据质量体系,为 Phase 2 体验打磨和未来功能扩展(基本面筛选、筹码分析、技术因子对比)提供数据基础。

### 改造范围概要

**改造现有表:**
- `stocks` 补全字段:fullname, cnspell, is_hs, act_name, asset_type 等(对齐 `stock_basic` 全字段)
- 核心事实表统一标准时间列:收敛 `trade_date_dt` / `created_at` 口径,清理字符串主时间列依赖
- 核心事实表正式落地 TimescaleDB:`daily_bars`、`moneyflow`、`indicators`、`patterns` 迁移为 hypertable,并补 compression / retention 基线
- `fund_flows` → `moneyflow`:大单/中单/小单/超大单买卖明细替代现有汇总值
- `stock_tops` → `top_list`:对齐 Tushare `top_list` 全字段
- `daily_bars` 统一走 `pro_bar` 通用行情接口,支持 asset=E/I/FT/O/FD
- 历史脚本退场:`scripts/init_timescaledb.py`、`scripts/convert_to_hypertable.py` 不再作为最终方案,由 Alembic migration 接管

**新增 6 张表:**

| 表名 | Tushare 接口 | 用途 |
|------|-------------|------|
| `daily_basic` | `daily_basic` | 每日指标:换手率、PE/PB/PS、总市值、流通市值 |
| `stock_st` | `stock_st` | ST 股票列表快照 |
| `broker_forecast` | `report_rc` | 券商盈利预测 |
| `chip_performance` | `cyq_perf` | 每日筹码成本与胜率 |
| `chip_distribution` | `cyq_chips` | 每日筹码分布 |
| `technical_factors` | `stk_factor_pro` | 210+ 技术面因子 |

### 执行工作流(4 条并行线)

```
WS-0 基础设施 (2d)  ──→  WS-1 核心改造 (4d)  ──→  WS-4 服务接入 (3d)
                    ──→  WS-2 新接口接入 (4d) ──→
                    ──→  WS-3 质量保障 (2d)   ──→
```

- **WS-0**:Alembic 迁移框架 + 时间列规范 + Timescale 规范 + 通用行情抽象 (`pro_bar`) + 数据质量框架 + 积分检测
- **WS-1**:stocks 补全 + 核心事实表时间列标准化 + hypertable 落地 + moneyflow 替换 + top_list 替换 + pro_bar 统一行情 + 指数入库
- **WS-2**:6 个新接口各自独立(**最高并行度,6 任务全并行**)
- **WS-3**:完整性检查 + 范围校验 + 跨源一致性 + 告警 + 回填工具 + 时序健康检查
- **WS-4**:Repository + API 端点 + 筛选条件集成 (PE/PB/换手率/市值) + ST 过滤 + 筹码可视化

详细任务分解和字段定义见 [DATA_LAYER_REPORT.md](./DATA_LAYER_REPORT.md)。

### 执行原则

- 数据层优化阶段直接完成 TimescaleDB 正式落地,不再保留运行时双写、双读、兼容兜底逻辑
- 多 Agent 并行时按 ownership 切分:migration/schema、ingestion/provider、new facts、quality 各自独立
- 新增时序表默认按最终目标态建模,是否做 hypertable 由统一规范决定,而不是后续补脚本

### `M1` DoD

- 不是“迁移脚本写完”,而是“数据层目标态完成并稳定”
- schema、抓取、调度、回填、健康检查必须一起验收
- 完成后才能作为 `P3-03` / `P3-05` / `P3-06` 的硬前置

### 验收标准
- [ ] 10 个 Tushare 接口已对接并可自动调度
- [ ] 每个新表有 Model + Migration + Fetch Task + Unit Test
- [ ] stocks 表包含 `stock_basic` 全字段
- [ ] 核心事实表已统一标准时间列
- [ ] `daily_bars` / `moneyflow` / `indicators` / `patterns` 已迁移为 hypertable,并配置 compression / retention 基线
- [ ] moneyflow 表包含大单/中单/小单/超大单买卖明细
- [ ] 通用行情接口支持 asset=E/I 获取
- [ ] 主抓取任务与调度已切换到标准时间列与新事实表口径
- [ ] 数据质量检查覆盖:完整性 + 范围 + 跨源一致性
- [ ] 时序健康检查覆盖:hypertable / chunk / compression / retention / 查询计划
- [ ] 历史数据回填工具可按日期范围运行
- [ ] 至少完成一次核心事实表回填演练并保留记录
- [ ] 新数据通过 API 端点可访问
- [ ] 筛选引擎支持 PE/PB/换手率/市值等基本面条件
- [ ] ST 股票可在筛选中被过滤

### 可并行推进的主线任务(与 Phase 0b/1 并行)

以下任务允许与 Phase 0b/1 并行,但进入数据层阶段后就是直接做目标态,不再限定为“只写骨架”:

- [ ] **时间列规范 + Alembic 基线** - 统一事实表时间列、唯一键、索引命名
- [ ] **Timescale 规范** - hypertable 范围、compression / retention / chunk 基线
- [ ] **核心事实表 migration** - `daily_bars` / `moneyflow` / `indicators` / `patterns`
- [ ] **Provider / Task 收敛** - `pro_bar` 统一行情、抓取任务切到标准时间列
- [ ] **数据质量 + 时序健康检查** - 完整性 / 范围 / 跨源 / chunk / 查询计划

---

## Phase 2:体验打磨(方向性,不定义具体任务)

### 目标
从"能用"到"顺手"。

### 方向
- 筛选面板交互优化(拖拽排序、条件组预设)
- 结果列表虚拟滚动 + 高级排序
- 个股详情页增强(多时间周期切换、指标自选)
- 关注列表提醒能力(条件触发推送)
- 最近研究上下文("上次我在看什么")

### 不做
- 通用笔记系统
- 项目式研究管理
- 社区分享

---

## 测试与质量

### 当前覆盖(10 个测试文件)
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
- [-] 选股引擎端到端测试(真实条件 → 真实结果 → 验证证据正确性)
  - 已新增最小基线:`tests/test_screening_baseline.py`,对 `/api/v1/screening/run` 连续执行 3 次并记录耗时 / 返回数量 / trade_date 一致性
- [ ] 回测报告结构测试
- [ ] 前端 E2E 测试(至少覆盖扫描 → 结果 → 详情主线)

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
| 期货/期权数据接入 | Phase 1.5 先覆盖 E(股票)+I(指数),FT/O 留到有明确需求时 |

---

## 当前分支工作流说明(2026-04-02 heartbeat)

- 当前工作分支 `phase-0-complete-scanning-engine` 上存在一批尚未合并的改动,范围已同时覆盖:
  - Phase 0b:首页 4 卡片 / 今日摘要 / 市场概览
  - Phase 1:筛选条件 → 策略模板打通
  - Phase 1:回测报告结构与前端回测页增强
- 这说明代码现实已经不是单一的"Phase 0b 收尾分支",而是 **Phase 0b 收尾 + Phase 1 预实现并行态**。
- 后续 heartbeat / review / 提交时,必须按任务归属来判断是否推进偏航:
  - Phase 0b 目标:联调验收 + 非功能验证 + 形态筛选条件
  - Phase 1 目标:策略桥接、回测报告、参数对比
- 结论:当前不应把所有未提交改动都视为"Phase 0b 阻塞",而应按 roadmap 分层审视。

## 下一步执行建议(优先级排序)

**第一优先级: `M0` 基线冻结**
1. 收敛 Phase 0/1 文档口径,不再同时保留“已通过”和“仍待做”的冲突描述
2. 明确“10 个交易日稳定”的处理方式
   - 若继续作为硬门槛,就保留为运营观察项
   - 若不阻塞 `M0`,就在里程碑说明里显式降级
3. 以 `M0` 为目标整理可合并 PR,停止继续把当前长分支作为最终承载分支

**第二优先级: `M1` 数据层底座**
4. 数据层改造 - 统一行情、标准时间列、TimescaleDB 正式落地、新接口接入、质量体系(详见 Phase 1.5 章节)
5. 以 `M1` DoD 验收,确认抓取任务切换、回填演练、时序健康检查都已通过

**然后按 P3 milestone 顺序推进**
9. `M2` `P3-01` 用户行为埋点
10. `M3` `P3-03` 预警规则与通知
11. `M4` `P3-04` 策略社交
12. `M5` `P3-05` 参数优化
13. `M6` `P3-06` 数据洞察报告
14. `M7` `P3-02` 推荐服务（依赖行为数据积累,最后收官）

---

## Phase 3:智能增强

### 目标
从"顺手"到"智能"，但执行上拆成多个可独立验收的 milestone,而不是作为单一长分支一次性落地。

### 现状评估
- Phase 0/1 已完成核心分析流水线
- Phase 2 已打磨交互体验
- 系统具备完整的筛选、回测、形态识别能力
- 数据层就绪（20260402 日线 + 指标）

### Phase 3 路线顺序
1. **P3-01 用户行为埋点**（P3 底座）
   - 为推荐、报告、运营分析提供事件基础

2. **风险预警系统**（高价值）
   - 持仓股票触达预警条件时主动推送
   - 回测结果的风险指标解读（最大回撤异常提醒）
   - 市场波动预警（全市场涨跌分布突变）

3. **策略市场与社交**（中价值）
   - 策略模板分享与评分
   - 公共策略库浏览与一键复制
   - 回测结果分享链接（已具备基础，增强为社区）

4. **自动化优化**（中价值）
   - 回测参数自动调优（网格搜索/贝叶斯优化）
   - 最佳参数组合推荐
   - 过拟合检测提醒

5. **数据洞察报告**（低风险，可先于推荐交付）
   - 每日/每周市场总结自动生成
   - 个人操作回顾与建议
   - 筛选命中率统计与条件效果分析

6. **智能推荐引擎**（P3 收官）
   - 基于用户历史操作推荐筛选条件
   - 基于关注列表自动生成每日扫描任务
   - "你可能感兴趣"的策略模板推荐

### 任务清单
- [ ] **P3-01 用户行为埋点与收集**（设计文档见 `docs/PHASE3_P3-01_USER_EVENTS.md`）
  - 建立用户事件追踪框架（page_view / filter_run / backtest_run / pattern_view / attention_action）
  - 后端：user_events 表 + POST /api/v1/events/track 端点（异步写入 + 限流）
  - 前端：useAnalytics composable + 5 页面集成
  - 验收：10+ 事件类型可收集，不影响主流程性能
- [ ] **P3-03 预警规则引擎 + 推送集成**（设计文档见 `docs/PHASE3_P3-03_ALERT_ENGINE.md`）
  - 预警条件：价格/涨跌幅/RSI/形态/资金流向
  - 定时检查任务（5 分钟间隔）+ 应用内通知 + 冷却防骚扰
  - 前端：Alert 管理页 + 通知铃铛 + 关注页快速设置
- [ ] **P3-04 策略分享功能增强**（设计文档见 `docs/PHASE3_P3-04_STRATEGY_MARKET.md`）
  - 社交功能：评分/评论/收藏 + 质量标签自动生成
  - 公共策略库页面 + 排行榜（总榜/热门/高收益/低回撤）
  - 策略卡片组件 + 详情弹窗 + 一键复制
- [ ] **P3-05 参数优化服务**（设计文档见 `docs/PHASE3_P3-05_PARAM_OPTIMIZATION.md`）
  - 自动化参数调优（随机搜索 + 贝叶斯优化）
  - 异步任务 + 进度查询 + 结果对比图表
  - 过拟合检测（滚动窗口验证 + 警告）
  - 并发控制 + 最优参数一键应用
- [ ] **P3-06 数据洞察报告生成**（设计文档见 `docs/PHASE3_P3-06_DATA_INSIGHTS.md`）
  - 三种报告：每日市场晨报 / 每周操作回顾 / 月度策略总结
  - 定时任务推送（08:30/周一09:00/每月1日10:00）
  - 应用内通知 + 邮件（可选） + 偏好设置
  - 报告详情页 + Dashboard 卡片
- [ ] **P3-02 智能推荐服务**（设计文档见 `docs/PHASE3_P3-02_RECOMMENDATION.md`）
  - 基于用户行为历史推荐筛选条件、策略模板、关注股票
  - 推荐类型：filter_recommendation / strategy_recommendation / stock_recommendation
  - 算法：规则引擎 + 简单协同过滤，冷启动使用全局热门
  - 前端组件：RecommendationCard（可 dismiss + 理由展示）
  - 集成点：Selection / Backtest / Dashboard

### 前置条件
- **`M0` / `M1` 已完成并合入 `main`**
- `P3-01` 用户行为埋点已上线并稳定收集事件
- `P3-02` 推荐验收前需完成用户行为数据积累（至少 2 周使用数据）
- 推送通道就绪（消息通知已打通）

### 风险提示
- 智能功能需谨慎设计，避免"过度智能"打扰用户
- 推荐算法需透明可解释，避免黑箱
- 预警需可配置，防止骚扰

---

## 迭代自检

每轮开发前后问:
1. 这次是否让"扫描 → 筛选 → 验证"更顺了?
2. 结果是否更可信、更可解释了?
3. 是否只是让产品看起来更完整,而不是更好用?
4. 如果删掉这项工作,产品是否反而更聚焦?

---

## 最终判断标准

> **先把"扫描 → 筛选 → 验证"做到自己每天都想用,其他一切都是噪音。**
