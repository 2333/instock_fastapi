# M1 启动就绪总览（Phase 1.5 数据层底座）

> 历史说明: 本文档保留为 2026-04-05 的旧 readiness 总览快照。当前重启口径以 `docs/milestones/m1/M1_RESTART_PLAN.md` 为准；本文中引用的 `scripts/check_m1_readiness.py` 已不再保证存在。本文中的 “等待 Tushare Token 修复” 是旧版本启动条件，不再代表当前阶段 M1 的唯一 go/no-go 判断。
>
> 状态: 历史快照（旧口径曾要求等待 Tushare Token 修复）
> 最后更新: 2026-04-05 03:59
> 触发条件: `scripts/check_m1_readiness.py` 返回所有 ✅

---

## 执行摘要

M1 (Phase 1.5 数据层改造) 全部准备工作已完成，包含:
- ✅ 四条工作流拆解 (WS-0/1/2/3)，64 项具体任务
- ✅ 环境就绪检查脚本（旧检查结论：TimescaleDB/Database/Alembic 已就绪，当时仅 Tushare token 被视为阻塞）
- ✅ 稳定性监测机制（每日 heartbeat 自动运行）
- ✅ 进度跟踪模板与启动清单

**历史阻塞记录**: 2026-04-05 时点的旧口径将 Tushare token 失效视为唯一阻塞；当前阶段已改为 token-independent 收口，不再沿用该判断。

---

## 历史环境检查状态

```bash
$ python scripts/check_m1_readiness.py
```

| 检查项 | 状态 | 详情 |
|--------|------|------|
| TimescaleDB 扩展 | ✅ 可用 | `SELECT * FROM pg_extension WHERE extname='timescaledb'` 确认 |
| 数据库连接 | ✅ 正常 | config tests 通过 |
| Alembic 工具 | ✅ 1.18.4 | `alembic --version` 可用 |
| Tushare Token | ❌ 历史阻塞记录 | API 返回 40101 "token 不对" |

**当时的修复命令**（用户操作）:
```bash
# 1. 登录 https://tushare.pro 重置 Token
# 2. 更新 .env 文件
sed -i '' "s/^TUSHARE_TOKEN=.*/TUSHARE_TOKEN=你的新token/" .env
# 3. 验证
python scripts/check_m1_readiness.py
```

参考: `docs/milestones/m1/M1_TUSHARE_TOKEN_BLOCK.md`

---

## 已准备的文档资产

| 文档 | 路径 | 说明 |
|------|------|------|
| M1 总体执行计划 | `docs/milestones/m1/M1_INITIATION_TASKS.md` | 四条工作流、验收标准、风险缓解 |
| 任务详细拆解 | `docs/milestones/m1/M1_TASK_BREAKDOWN.md` | 64 项任务，含步骤、输出、验收、工时 |
| 进度跟踪模板 | `docs/milestones/m1/M1_PROGRESS_TRACKER.md` | 状态跟踪（todo/in_progress/done/blocked） |
| 启动检查清单 | `docs/milestones/m1/M1_KICKOFF_CHECKLIST.md` | 触发条件 → 自动执行序列 → 验收 |
| 环境就绪检查脚本 | `scripts/check_m1_readiness.py` | 4 项检查 + JSON 摘要 + go/no-go |
| 稳定性监测脚本 | `scripts/monitor_stability.py` | 每日自动记录（trade_date/task_health/quick_suite） |
| Tushare 阻塞诊断 | `docs/milestones/m1/M1_TUSHARE_TOKEN_BLOCK.md` | API 40101 诊断、修复步骤、临时方案 |
| 快速修复指南 | `docs/milestones/m1/M1_TUSHARE_TOKEN_BLOCK.md` | Tushare token 修复指南 |
| **本总览** | `docs/milestones/m1/M1_READINESS_SUMMARY.md` |  consolidated readiness state |

---

## M1 四条工作流概览

```
WS-0: 基础设施 (前置, 2d)
├── WS0-01 Alembic 基线
├── WS0-02 时间列规范
├── WS0-03 Timescale 规范
├── WS0-04 pro_bar 抽象
└── WS0-05 质量框架骨架
     ↓
WS-1: 核心改造 (依赖 WS-0, 4d)
├── WS1-10 stocks 补全字段
├── WS1-11 daily_bars 时间列标准化
├── WS1-12 daily_bars hypertable
├── WS1-13 moneyflow 替换 fund_flows
├── WS1-14 top_list 替换 stock_tops
├── WS1-15 indicators/patterns 迁移
└── WS1-16 pro_bar 切换主抓取
     ↓
WS-2: 新接口接入 (与 WS-1 并行, 1.5d)
├── daily_basic (2000+ 积分)
├── stock_st (3000+ 积分)
├── broker_forecast (8000+ 积分)
├── chip_performance (5000+ 积分)
├── chip_distribution (5000+ 积分)
└── technical_factors (5000+ 积分)
     ↓
WS-3: 质量保障 (与 WS-1/2 并行, 2d)
├── WS3-31 完整性检查
├── WS3-32 范围校验
├── WS3-33 跨源一致性
├── WS3-34 告警与监控
├── WS3-35 回填工具
└── WS3-36 时序健康检查
```

**总并行工期**: WS-0 (2d) → WS-1 (4d) + WS-2 (1.5d) + WS-3 (2d) → 约 4-5 天完成 M1

---

## 历史触发流程（旧口径）

### 阶段 1: M0 合并确认
- [ ] PR #8 已合入 `main`
- [ ] 本地 `main` 分支已拉取最新

### 阶段 2: WS-0 第一批任务启动
按 `docs/milestones/m1/M1_KICKOFF_CHECKLIST.md` 执行:
1. Agent A: Alembic 基线初始化
2. Agent A: 时间列规范迁移
3. Agent A: Timescale 规范迁移
4. Agent B: pro_bar 抽象实现
5. Agent F: 质量框架骨架

### 阶段 3: 进度跟踪初始化
- 创建/更新 `docs/milestones/m1/M1_PROGRESS_TRACKER.md`
- 将所有 WS-0 任务状态改为 `in_progress`
- 记录开始日期与负责人

---

## 历史 M1 完成验收标准（旧口径）

- [ ] WS-0 全部 5 项任务 done
- [ ] WS-1 核心改造 7 项完成
- [ ] WS-2 新接口 6 张表全部接入（旧口径；当前阶段已缩窄为 token-independent 范围）
- [ ] WS-3 质量体系运行并通过至少 1 次回填演练
- [ ] 新增数据可通过 API 访问
- [ ] 测试覆盖新增模块（新增测试 ≥ 对应任务数 50%）
- [ ] 文档更新（DATA_LAYER_REPORT.md 与实现一致）

---

## 历史风险与降级策略

| 风险 | 影响 | 降级方案 |
|------|------|---------|
| Tushare 积分不足 3000 | 无法使用 daily_basic/stock_st 等基础接口 | 使用 EastMoney/BaoStock 降级源，功能受限 |
| Tushare 积分不足 8000 | broker_forecast/chip_*/technical_factors 无法接入 | 标记为 Phase 2 增强，M1 先完成基础部分 |
| TimescaleDB 未安装 | hypertable 无法创建 | 暂时使用普通 PostgreSQL 表，后续迁移 |
| 历史数据回填超时 | 阻塞验证 | 先做单日回填演练，再扩展到范围 |

---

## 快速命令参考

```bash
# 环境就绪检查
python scripts/check_m1_readiness.py

# 稳定性监测（每日）
python scripts/monitor_stability.py

# M0 合并后切换分支
git checkout main
git pull origin main

# WS-0 示例：Alembic 基线
alembic init alembic/
# 配置 alembic.ini 与 env.py（参考 M1_TASK_BREAKDOWN.md）
alembic revision --autogenerate -m "baseline"
alembic upgrade head

# 运行快速回归套件（Phase 0/1）
source .venv/bin/activate
pytest tests/test_screening_baseline.py tests/test_api.py::TestMarketTaskHealthAPI tests/test_selection_market_services.py tests/test_selection_today_summary.py tests/test_backtest_report_structure.py tests/test_strategy_selection_bridge.py -q
```

---

## 相关文档链接

- **总体计划**: `docs/milestones/m1/M1_INITIATION_TASKS.md`
- **任务拆解**: `docs/milestones/m1/M1_TASK_BREAKDOWN.md`
- **进度跟踪**: `docs/milestones/m1/M1_PROGRESS_TRACKER.md`（运行时更新）
- **启动清单**: `docs/milestones/m1/M1_KICKOFF_CHECKLIST.md`
- **阻塞诊断**: `docs/milestones/m1/M1_TUSHARE_TOKEN_BLOCK.md`
- **快速修复**: `docs/milestones/m1/M1_TUSHARE_TOKEN_BLOCK.md`
- **数据层设计**: `docs/milestones/m1/DATA_LAYER_REPORT.md`
- **里程碑路线**: `docs/EXECUTION_PLAN.md`

---

**维护说明**: 本文件由 heartbeat 自动更新阻塞状态，M1 启动后转为进度报告。
