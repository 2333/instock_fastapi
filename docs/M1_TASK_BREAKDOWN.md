# M1 任务拆解与 Agent 分配计划

> 版本: 2026-04-05
> 基于: docs/M1_INITIATION_TASKS.md + docs/DATA_LAYER_REPORT.md
> 目的: M0 合入后可直接分派给 Agents 执行，无需再拆

---

## 执行策略

- **并行度**: 4 个工作流（WS-0 前置，WS-1/2/3 并行）
- **Agent 分配**: 每个 WS 指定负责人，任务按依赖顺序执行
- **验收方式**: 每个任务必须提供可验证的输出（迁移脚本、测试、文档）
- **进度跟踪**: 任务状态更新到 `docs/M1_PROGRESS_TRACKER.md`

---

## WS-0: 基础设施层（前置，2 天）

**负责人**: Agent A (Database Migration Specialist)

### Task WS0-01: Alembic 基线与迁移入口

**描述**: 建立 Alembic 迁移框架，替代现有 `init_db()` auto-create 逻辑。

**具体步骤**:
1. 安装 Alembic: `pip install alembic`
2. 初始化: `alembic init alembic/`
3. 配置 `alembic.ini` 与 `alembic/env.py` 指向现有数据库 URL
4. 在 `app/database.py` 添加 `run_migrations()` 函数，应用启动时可选调用
5. 生成基准迁移: `alembic revision --autogenerate -m "baseline"`

**输出**:
- `alembic/` 目录（versions/, script.py.mako, env.py）
- `app/database.py` 新增 `run_migrations()` 入口
- `docs/MIGRATION_CONVENTIONS.md`（命名、依赖、回滚规范）

**验收**:
```bash
alembic current  # 显示当前版本
alembic upgrade head  # 无错误完成
```

**依赖**: 无
**预计工时**: 0.5 天

---

### Task WS0-02: 时间列与唯一约束规范

**描述**: 统一事实表时间列与主键规范，生成迁移脚本。

**具体步骤**:
1. 定义标准列名:
   - 时间列: `trade_date_dt` (DateTime) + `created_at` (Timestamp)
   - 旧列: `trade_date` (字符串) 废弃
2. 唯一约束: `(ts_code, trade_date_dt)` 联合主键
3. 索引命名: `ix_{table}_{column}` 格式
4. 更新 Model (SQLAlchemy):
   - `DailyBar`, `Moneyflow`, `Indicators`, `Patterns` 添加新列
   - 废弃旧 `trade_date` 映射
5. 生成迁移: `alembic revision --autogenerate -m "standardize-time-columns"`
6. 审查迁移 SQL，确保数据迁移逻辑正确

**输出**:
- Model 更新（app/models/ 下相关文件）
- Alembic 迁移脚本（含数据迁移：将 `trade_date` 字符串转为 `trade_date_dt`）
- `docs/SCHEMA_CONVENTIONS.md`（字段命名、类型、约束规范）

**验收**:
- 迁移可执行，数据不丢失
- `alembic history` 显示新版本
- 测试环境数据库结构更新成功

**依赖**: WS0-01 (Alembic 框架)
**预计工时**: 0.5 天

---

### Task WS0-03: Timescale 规范与策略

**描述**: 定义 hypertable 策略，生成创建 Timescale 对象的迁移。

**具体步骤**:
1. 确认 TimescaleDB 扩展已安装: `CREATE EXTENSION IF NOT EXISTS timescaledb;`
2. 定义 hypertable 表:
   - `daily_bars` (按 `trade_date_dt` + `ts_code` 分块？不，Timescale 单维度时间分区即可，`ts_code` 作为普通列)
   - `indicators`
   - `patterns`
   - `moneyflow` (新增表，直接创建为 hypertable)
3. chunk 间隔: 建议 7 天（可后续调整）
4. compression: 启用，30 天后自动压缩
5. retention: 暂不设置（保留全部历史）
6. 生成迁移: 手动编写 SQL 或使用 Alembic op.execute()

**输出**:
- Alembic 迁移（含 `CREATE TABLE ...` + `SELECT create_hypertable(...)`）
- `docs/TIMESCALE_POLICY.md`（chunk/compression/retention 参数与调整方法）

**验收**:
```sql
SELECT * FROM timescaledb_information.hypertables;
-- 应看到 daily_bars, indicators, patterns, moneyflow
```

**依赖**: WS0-02 (表结构已定)
**预计工时**: 0.5 天

---

### Task WS0-04: 通用行情接口抽象 (pro_bar)

**描述**: 实现 `fetch_pro_bar` 统一行情获取入口，支持多资产类型。

**具体步骤**:
1. 在 `app/services/` 下创建 `pro_bar.py`（或在 `tushare_provider.py` 添加方法）
2. 实现 `fetch_pro_bar(ts_code, asset="E", freq="D", adj=None, start_date, end_date)`:
   - asset=E: 股票日线 → `pro.daily()`
   - asset=I: 指数日线 → `pro.index_daily()`
   - 返回标准化 DataFrame: `ts_code, trade_date, open, high, low, close, vol, amount, adj_factor`
3. 添加字段映射与类型转换（trade_date 转为 `datetime`）
4. 编写单元测试（覆盖 E/I 两种资产）

**输出**:
- `app/services/pro_bar.py` (或扩展 `TushareProvider`)
- 测试: `tests/test_pro_bar.py`

**验收**:
- 测试通过: `pytest tests/test_pro_bar.py -q`
- 可实际获取 000001.SZ 与 000001.SH 数据

**依赖**: 无（可独立开发）
**预计工时**: 1 天

---

### Task WS0-05: 数据质量框架骨架

**描述**: 建立质量检查框架，为 WS-3 后续填充检查项提供扩展点。

**具体步骤**:
1. 创建 `app/services/data_quality.py`
2. 定义抽象基类/接口:
   - `class DataQualityCheck(Protocol): run() -> CheckResult`
   - `class CheckResult: passed: bool, details: dict, suggestions: list[str]`
3. 实现占位检查项（始终 PASS）:
   - `CompletenessCheck`
   - `RangeCheck`
   - `CrossSourceConsistencyCheck`
4. 提供 CLI 入口 `scripts/run_quality_checks.py`:
   - 加载所有检查项
   - 输出 JSON 报告
5. 集成到 heartbeat（可选，后续 WS-3 填充）

**输出**:
- `app/services/data_quality.py`
- `scripts/run_quality_checks.py`
- 基础测试 `tests/test_data_quality.py`

**验收**:
- 框架可运行: `python scripts/run_quality_checks.py` 返回 JSON 且 exit code 0
- 测试通过

**依赖**: 无
**预计工时**: 0.5 天

---

## WS-1: 核心数据改造（依赖 WS-0 完成）

**负责人**: Agent C (Data Model & Migration)

任务序列（按顺序执行）:

| Task | 描述 | 依赖 | 工时 |
|------|------|------|------|
| WS1-10 | stocks 表补全字段（fullname/cnspell/is_hs/act_name 等） | WS0-02 | 1d |
| WS1-11 | daily_bars 时间列标准化（trade_date → trade_date_dt） | WS0-02 | 0.5d |
| WS1-12 | daily_bars 转换为 hypertable | WS0-03 | 0.5d |
| WS1-13 | moneyflow 替换 fund_flows（新表 + 数据迁移） | WS0-02 | 1d |
| WS1-14 | top_list 替换 stock_tops（新表 + 数据迁移） | WS0-02 | 1d |
| WS1-15 | indicators/patterns 时间列标准化 + hypertable | WS0-02/03 | 1d |
| WS1-16 | 主抓取任务切换到 pro_bar（fetch_daily_task 改造） | WS0-04 | 1d |

**总工期**: 约 4 天（含并行与串行）

---

## WS-2: 新接口接入（与 WS-1 并行，全部独立）

**负责人**: Agent D (Data Ingestion)

6 个接口可完全并行开发，每个包含:
- Model 定义 (SQLAlchemy)
- Alembic 迁移（创建表）
- Provider fetch 函数实现
- Scheduler 任务注册（每日定时）
- 单元测试（model + provider）

| 接口 | 表名 | 积分要求 | 预计工时 | 说明 |
|------|------|----------|---------|------|
| daily_basic | daily_basic | 2000+ | 1d | 换手率/PE/PB/市值 |
| stock_st | stock_st | 3000+ | 0.5d | ST 标记（筛选过滤用） |
| broker_forecast | broker_forecast | 8000+ | 1d | 券商预测（可能积分不足） |
| chip_performance | chip_performance | 5000+ | 1d | 筹码胜率 |
| chip_distribution | chip_distribution | 5000+ | 1d | 筹码分布 |
| technical_factors | technical_factors | 5000+ | 1.5d | 210+ 因子（最大） |

**总并行工期**: 约 1.5 天（最长的 technical_factors 决定）

**注意**: 若 Tushare 积分不足，标记为 "暂不可用"，延后实现。

---

## WS-3: 质量保障（与 WS-1/2 并行，后置依赖）

**负责人**: Agent F (Quality & Observability)

任务序列:

| Task | 描述 | 依赖 | 工时 |
|------|------|------|------|
| WS3-31 | 完整性检查（每日数据行数 vs Tushare 基准） | WS1-04/WS2 完成 | 0.5d |
| WS3-32 | 范围校验（日期范围、代码覆盖度） | WS1-04/WS2 | 0.5d |
| WS3-33 | 跨源一致性（Tushare vs EastMoney 对比） | WS1-04/WS2 | 0.5d |
| WS3-34 | 告警与监控（失败/缺失率阈值） | WS3-31 | 0.5d |
| WS3-35 | 回填工具（按日期范围回填历史数据） | WS1-04/WS2 | 0.5d |
| WS3-36 | 时序健康检查（hypertable/chunk/compression/查询计划） | WS0-03 | 0.5d |

**总工期**: 约 2 天（部分任务可并行）

---

## 进度跟踪

创建 `docs/M1_PROGRESS_TRACKER.md`，每个任务包含:
- 状态: `todo` / `in_progress` / `done` / `blocked`
- Owner
- 开始/完成日期
- 交付物链接
- 阻塞原因

---

## 决策待办（人工，M1 启动前确认）

| 决策项 | 选项 | 建议 | 影响 |
|--------|------|------|------|
| Tushare 积分 | 确认当前等级（3000+ / 8000+） | 检查账号，不足则降级实现 | 决定 WS-2 接口范围 |
| TimescaleDB 环境 | 开发/生产是否已安装扩展 | 运行 `SELECT * FROM pg_extension WHERE extname='timescaledb'` | 决定 WS-0 能否通过 |
| Agent 分配 | 是否使用子 Agent 并行 | WS-2 6 个任务可并行分派 | 影响总工期 |
| M0 合并时机 | 立即合并 vs 延迟 | 建议立即合并以启动 M1 | 决定整体进度 |

---

**下一步**:
1. Opus 合并 PR #8
2. 确认 Tushare 积分与 TimescaleDB 环境
3. 启动 WS-0 第一批任务（Alembic 基线）
4. 创建 `M1_PROGRESS_TRACKER.md` 并分配任务给 Agents
