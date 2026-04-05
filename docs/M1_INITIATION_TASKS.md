# M1 启动任务板：Phase 1.5 数据层底座

> 版本: 2026-04-05
> 状态: 准备就绪，待 M0 合并后立即启动
> 并行工作流: WS-0 → WS-1/WS-2/WS-3（WS-0 为前置）

---

## 执行摘要

M1 目标：完成数据层目标态，为 P3-03/P3-05/P3-06 提供稳定底座。

**四条并行线**:
- **WS-0 基础设施** (前置，2 天): Alembic 迁移框架 + 时间列规范 + Timescale 规范 + 通用行情抽象 + 数据质量框架
- **WS-1 核心改造** (依赖 WS-0，4 天): stocks 补全 + 核心事实表时间列标准化 + hypertable 落地 + moneyflow/top_list 替换 + pro_bar 统一行情
- **WS-2 新接口接入** (与 WS-1 并行，4 天): 6 个新表各自独立（daily_basic / stock_st / broker_forecast / chip_performance / chip_distribution / technical_factors）
- **WS-3 质量保障** (与 WS-1/2 并行，2 天): 完整性检查 + 范围校验 + 跨源一致性 + 告警 + 回填工具 + 时序健康检查

**验收标准**:
- 至少 1 次核心事实表回填演练完成并留痕
- 新数据通过 API 端点可访问
- 时序健康检查覆盖 hypertable/chunk/compression/retention/查询计划

---

## WS-0: 基础设施层（第一批任务，立即启动）

### M1-01: Alembic 基线与迁移入口统一

**Owner**: Agent A (DB migration specialist)
**工期**: 0.5 天
**输出**:
- `alembic/` 目录与 `alembic.ini`
- `app/database.py` 增加 `run_migrations()` 入口
- 迁移规范文档（单次迁移命名、依赖、回滚策略）

**验收**:
- `alembic current` 显示基础版本
- `alembic upgrade head` 可执行且无错误

---

### M1-02: 时间列与唯一约束规范落地

**Owner**: Agent A
**工期**: 0.5 天
**输出**:
- 事实表时间列统一为 `trade_date_dt` (DateTime) + `created_at` (Timestamp)
- 唯一约束规范: `(ts_code, trade_date_dt)` 为联合主键
- 索引命名规范: `ix_{table}_{column(s)}`

**文件**:
- `docs/DATA_LAYER_REPORT.md` 已定义规范
- 新增 `docs/MIGRATION_CONVENTIONS.md` 记录决策

**验收**:
- 核心表（daily_bars/indicators/patterns/moneyflow）的 model 已按新规范定义
- 迁移脚本生成并审查通过

---

### M1-03: Timescale 规范落地

**Owner**: Agent A
**工期**: 0.5 天
**输出**:
- hypertable 范围: 按 `trade_date_dt` 分区
- chunk 间隔: 建议 7 天（可配置）
- compression: 启用，策略 30 天
- retention: 暂不设置（保留全部历史）
- 规范文档: `docs/TIMESCALE_POLICY.md`

**验收**:
- `alembic` 迁移包含 `CREATE EXTENSION timescaledb`（如未安装）
- 示例表（如 indicators）hypertable 创建成功
- `SELECT * FROM timescaledb_information.hypertables` 可验证

---

### M1-00: 通用行情接口抽象（pro_bar）

**Owner**: Agent B (Provider/Task)
**工期**: 1 天（与 WS-0 其他任务并行）
**输出**:
- `app/services/pro_bar.py` 或 `app/core/crawling/tushare_provider.py` 实现 `fetch_pro_bar`
- 支持 asset=E/I/FT/O/FD，freq=D/W/M，adj=qfq/hfq/None
- 返回标准化 DataFrame（列名统一）

**验收**:
- 股票日线获取正常（asset=E）
- 指数日线获取正常（asset=I）
- 字段映射符合 `daily_bars` model

---

### M1-00: 数据质量框架基础

**Owner**: Agent F (Quality/Observability)
**工期**: 0.5 天
**输出**:
- `app/services/data_quality.py` 框架结构
- 检查项接口：完整性、范围、跨源一致性（占位）
- `scripts/run_quality_checks.py` CLI 入口

**验收**:
- 框架可运行但不报错（检查项暂为 pass-through）
- 为 WS-3 后续填充留好扩展点

---

## WS-0 总体验收

- [ ] Alembic 迁移框架可用
- [ ] 时间列/约束规范已记录并应用到 model
- [ ] Timescale 策略文档就绪
- [ ] `pro_bar` 基础版本可获取股票/指数日线
- [ ] 数据质量框架骨架完成

**WS-0 完成后** → 解锁 WS-1 与 WS-2 并行推进。

---

## 后续任务（WS-0 完成后启动）

### WS-1 核心改造任务序列

| Task | 依赖 | 预计工期 | 说明 |
|------|------|---------|------|
| M1-10 stocks 表补全字段 | M1-02 | 1d | 执行迁移，补全 fullname/cnspell/is_hs/act_name 等 |
| M1-11 daily_bars 时间列标准化 | M1-02 | 0.5d | trade_date → trade_date_dt (DateTime)，数据迁移 |
| M1-12 daily_bars hypertable 化 | M1-03 | 0.5d | 转换为 Timescale hypertable |
| M1-13 moneyflow 替换 fund_flows | M1-02 | 1d | 新表 migration + provider 写入切换 |
| M1-14 top_list 替换 stock_tops | M1-02 | 1d | 新表 migration + provider 写入切换 |
| M1-15 indicators/patterns 迁移 | M1-02 | 1d | 时间列标准化 + hypertable |
| M1-16 pro_bar 切换主抓取任务 | M1-00 | 1d | fetch_daily_task 切到 pro_bar |

### WS-2 新接口接入（全部并行）

| 接口 | 表名 | 模型 | Provider | 预计工期 |
|------|------|------|----------|---------|
| daily_basic | daily_basic | DailyBasic | fetch_daily_basic | 1d |
| stock_st | stock_st | StockST | fetch_stock_st | 0.5d |
| broker_forecast | broker_forecast | BrokerForecast | fetch_broker_forecast | 1d |
| chip_performance | chip_performance | ChipPerformance | fetch_chip_performance | 1d |
| chip_distribution | chip_distribution | ChipDistribution | fetch_chip_distribution | 1d |
| technical_factors | technical_factors | TechnicalFactors | fetch_technical_factors | 1.5d |

**总并行工期**: 约 1.5 天（最长的 technical_factors 决定）

### WS-3 质量保障任务序列

| Task | 依赖 | 说明 |
|------|------|------|
| M1-31 完整性检查 | M1-04/M1-06 | 每日数据行数 vs Tushare 基准 |
| M1-32 范围校验 | M1-04/M1-06 | 日期范围、代码覆盖度 |
| M1-33 跨源一致性 | M1-04/M1-06 | Tushare vs EastMoney 关键字段对比 |
| M1-34 告警与监控 | M1-31 | 失败/缺失率阈值告警 |
| M1-35 回填工具 | M1-04/M1-06 | 按日期范围回填历史数据 |
| M1-36 时序健康检查 | M1-03 | hypertable/chunk/compression/查询计划验收 |

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Tushare 积分不足 | 部分接口无法接入 | 确认当前积分，降级使用可用接口，标注缺口 |
| TimescaleDB 未安装 | hypertable 无法创建 | 环境检查脚本，安装指导文档 |
| 历史数据回填耗时 | 阻塞验证 | 先做单日回填演练，再扩展到范围 |
| 迁移回滚复杂度 | 出错恢复困难 | 每个迁移带 `downgrade`，先在测试库演练 |

---

## 决策待办（人工）

1. **Tushare 积分确认**: 当前账号是否满足 3000+ / 8000+ 积分？
2. **TimescaleDB 环境**: 生产/开发库是否已安装 TimescaleDB 扩展？
3. **Agent 分配**: 是否按 WS 分给不同 Agent 并行执行？
4. **M0 合并时机**: 待 PR #8 合入后立即启动 WS-0

---

**下一步**: 等待 M0 PR #8 合入 → 启动 WS-0 第一批任务（Alembic 基线 + 时间列规范 + Timescale 规范 + pro_bar 抽象）。
