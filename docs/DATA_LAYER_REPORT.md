# InStock 数据层现状分析与优化计划

> 生成日期: 2026-04-02
> 范围: 数据获取、存储、质量管理全链路

---

## 一、现状分析

### 1.1 当前数据源架构

| 数据源 | 角色 | 获取内容 | 认证方式 |
|--------|------|----------|----------|
| **Tushare** | 主数据源 | 股票列表、日K线、资金流排名、龙虎榜、大宗交易 | Token (TUSHARE_TOKEN) |
| **东方财富 (EastMoney)** | 辅助/降级源 | A股列表、ETF、K线、资金流、涨停原因、大宗交易、分红 | 无需认证 |
| **BaoStock** | 降级备用 | 历史K线数据 | 无需认证 |

**降级策略**: Tushare → BaoStock → EastMoney (串行尝试)

### 1.2 当前数据库表结构

| 表名 | 用途 | 关键字段 | 时间范围 |
|------|------|----------|----------|
| `stocks` | 证券主表 | ts_code, symbol, name, area, industry, market, exchange, list_date, is_etf | 静态 |
| `daily_bars` | OHLCV K线 | ts_code, trade_date, open/high/low/close, vol, amount, adj_factor | 滚动3650天 |
| `fund_flows` | 资金流向 | ts_code, trade_date, net_amount_main/hf/zz/dt/xd | 滚动1095天 |
| `indicators` | 技术指标 | ts_code, trade_date, indicator_name, indicator_value | 滚动1095天 |
| `patterns` | K线形态 | ts_code, trade_date, pattern_name, pattern_type, confidence | 滚动365天 |
| `stock_tops` | 龙虎榜 | ts_code, trade_date, ranking_times, sum_buy, sum_sell, net_amount | - |
| `stock_block_trades` | 大宗交易 | ts_code, trade_date, avg_price, premium_rate, trade_count | - |
| `stock_bonus` | 分红送转 | ts_code, bonus_type, bonus_ratio, transfer_ratio, cash_ratio | - |
| `stock_limitup_reasons` | 涨停原因 | ts_code, trade_date, close_price, limitup_count, reason | - |
| `sector_fund_flows` | 板块资金流 | sector_name, sector_type, trade_date, net_amount_main | - |
| `north_bound_funds` | 北向资金 | ts_code, trade_date, sh/sz_net_inflow | - |

### 1.3 当前调度流水线

```
15:30 Mon-Fri  →  fetch_daily_data     (K线 OHLCV)
16:00 Mon-Fri  →  fetch_fund_flow      (资金流向)
21:15 Mon-Fri  →  fetch_market_ref     (龙虎榜 + 大宗交易)
后续链式执行   →  indicator_task       (TA-Lib 计算 MA/RSI/MACD)
              →  pattern_task         (K线形态识别)
              →  strategy_task        (策略选股执行)
              →  cleanup_task         (数据保留策略清理)
```

### 1.4 已识别的问题

#### 数据完整性问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **字段丢失** | Tushare返回的很多字段 (换手率、PE、PB、总市值等) 在入库时被丢弃 | 无法做基本面筛选 |
| **表结构不匹配** | `fund_flows` 只存 net_amount_*, 缺少买卖量细分 (大单/中单/小单/超大单) | 资金流分析维度不足 |
| **资产类型单一** | `daily_bars` 仅存股票，指数/基金/期货/期权无独立表或标记 | 无法做跨资产分析 |
| **stocks表字段不全** | 缺少 fullname, cnspell, curr_type, is_hs, act_name, act_ent_type | 搜索和筛选能力受限 |

#### 数据源管理问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **无数据质量评估** | 缺少对Tushare/EastMoney返回数据的一致性校验 | 不同源可能存在价格/成交量偏差 |
| **无跨源校验** | 同一数据从不同源获取后不做对比 | 数据错误无法发现 |
| **无ST标记** | 没有ST股票列表集成 | 筛选时无法剔除ST股票 |
| **缺少分析师预测** | 无券商盈利预测数据 | 缺失重要基本面参考 |
| **缺少筹码数据** | 无筹码分布和胜率数据 | 缺失重要技术面分析维度 |
| **缺少技术面因子** | 技术指标为自算 (TA-Lib)，未对比 Tushare 预算值 | 指标计算可能有偏差 |

#### 架构问题

| 问题 | 现状 | 影响 |
|------|------|------|
| **无通用行情抽象** | 股票/指数/ETF各走各的获取路径 | 扩展新资产类型需改多处代码 |
| **字段映射散落** | 每个 crawler 内部做字段映射，格式不统一 | 维护成本高，易出bug |
| **无数据版本管理** | 数据直接 upsert，无法回溯历史修订 | 分析结果不可复现 |

---

## 二、目标架构

### 2.1 核心设计原则

1. **统一入口**: 所有行情数据通过 `pro_bar` (通用行情接口) + 专项接口获取
2. **全字段保留**: Tushare 返回的所有字段均入库，不丢弃
3. **资产类型通用**: stocks 表和 daily_bars 表原生支持 E(股票)/I(指数)/FT(期货)/O(期权)/FD(基金)
4. **每接口对应一表**: 新增接口的数据有独立存储表，字段与 Tushare 文档一一对应

### 2.2 新增/改造数据表

#### 改造现有表

**`stocks` 表补全字段:**
```
+ fullname         VARCHAR(100)  -- 公司全称
+ enname           VARCHAR(200)  -- 英文名
+ cnspell          VARCHAR(20)   -- 拼音缩写
+ curr_type        VARCHAR(10)   -- 交易货币
+ list_status      VARCHAR(2)    -- L/D/P/G
+ delist_date      VARCHAR(10)   -- 退市日期
+ is_hs            VARCHAR(2)    -- 沪深港通标记
+ act_name         VARCHAR(100)  -- 实际控制人
+ act_ent_type     VARCHAR(50)   -- 实控人企业类型
+ asset_type       VARCHAR(5)    -- 资产类型: E/I/FT/O/FD/CB
```

**`fund_flows` 表升级为 `moneyflow`:**
```
替换: net_amount_main/hf/zz/dt/xd
为:   buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount,
      buy_md_vol, buy_md_amount, sell_md_vol, sell_md_amount,
      buy_lg_vol, buy_lg_amount, sell_lg_vol, sell_lg_amount,
      buy_elg_vol, buy_elg_amount, sell_elg_vol, sell_elg_amount,
      net_mf_vol, net_mf_amount
```

#### 新增表

| 表名 | 对应接口 | 主键/唯一约束 | 用途 |
|------|----------|--------------|------|
| `daily_basic` | `daily_basic` | (ts_code, trade_date) | 每日指标：换手率、PE/PB/PS、总市值、流通市值 |
| `stock_st` | `stock_st` | (ts_code, trade_date) | ST 股票列表快照 |
| `broker_forecast` | `report_rc` | (ts_code, report_date, org_name, quarter) | 券商盈利预测 |
| `chip_performance` | `cyq_perf` | (ts_code, trade_date) | 每日筹码成本与胜率 |
| `chip_distribution` | `cyq_chips` | (ts_code, trade_date, price) | 每日筹码分布 |
| `technical_factors` | `stk_factor_pro` | (ts_code, trade_date) | 210+ 技术面因子 |
| `top_list` | `top_list` | (ts_code, trade_date, reason) | 龙虎榜每日统计（替代现有 stock_tops） |

### 2.3 通用行情接口抽象

```python
# core/crawling/tushare_provider.py 新增方法

class TushareProvider:
    async def fetch_pro_bar(
        self,
        ts_code: str,
        asset: str = "E",       # E/I/FT/O/FD/CB
        freq: str = "D",        # D/W/M/min
        adj: str | None = None, # qfq/hfq/None
        start_date: str = "",
        end_date: str = "",
        ma: list[int] | None = None,
        factors: list[str] | None = None,
    ) -> pd.DataFrame:
        """统一行情数据获取入口"""
        ...
```

所有资产类型的日线数据获取统一走 `fetch_pro_bar`，内部按 `asset` 参数路由。

### 2.4 数据获取调度（增强后）

```
09:20  →  fetch_stock_meta     (股票列表 stock_basic + ST列表 stock_st) [每日]
15:30  →  fetch_daily_bars     (通用行情 pro_bar, asset=E)
15:45  →  fetch_index_bars     (通用行情 pro_bar, asset=I)
16:00  →  fetch_daily_basic    (每日指标 daily_basic)
16:15  →  fetch_moneyflow      (个股资金流向 moneyflow)
18:00  →  fetch_chips          (筹码胜率 cyq_perf + 筹码分布 cyq_chips)
19:00  →  fetch_tech_factors   (技术面因子 stk_factor_pro)
21:15  →  fetch_top_list       (龙虎榜 top_list)
22:00  →  fetch_broker_forecast(券商预测 report_rc) [每日增量]
后续   →  indicator_task / pattern_task / strategy_task / cleanup_task
```

---

## 三、Tushare 接口集成清单

### 3.1 接口详情

| # | 接口名 | endpoint | 积分要求 | 单次最大行数 | 数据起始 | 频率限制 |
|---|--------|----------|----------|-------------|---------|---------|
| 1 | 通用行情接口 | `pro_bar` | 600+ (分钟) | 按资产类型 | - | SDK only |
| 2 | 每日指标 | `daily_basic` | 2000+ | 6,000 | - | - |
| 3 | 股票列表 | `stock_basic` | 2000+ | 6,000 | - | 50次/分 |
| 4 | ST股票列表 | `stock_st` | 3000+ | 1,000 | 2016 | - |
| 5 | 券商盈利预测 | `report_rc` | 8000+ (完整) | 3,000 | 2010 | - |
| 6 | 每日筹码及胜率 | `cyq_perf` | 5000+ | 5,000 | 2018 | - |
| 7 | 每日筹码分布 | `cyq_chips` | 5000+ | 2,000 | 2018 | - |
| 8 | 技术面因子 | `stk_factor_pro` | 5000+ | 10,000 | 全历史 | 30次/分起 |
| 9 | 个股资金流向 | `moneyflow` | 2000+ | 6,000 | 2010 | - |
| 10 | 龙虎榜每日统计 | `top_list` | 2000+ | 10,000 | 2005 | - |

### 3.2 积分需求评估

- **基础功能** (接口 1-4, 9-10): 需 **3000+** 积分
- **进阶功能** (接口 5-8): 需 **8000+** 积分
- **建议**: 确认当前 Tushare 积分等级，优先实现积分范围内的接口

---

## 四、执行计划

### 4.1 分层设计

整个改造分为 **4个并行工作流 (Workstream)**, 每个工作流可由独立的人/Agent执行:

```
                           ┌─────────────────────────────────────────┐
                           │         WS-0: 基础设施层 (前置)          │
                           │ DB迁移框架 + Timescale规范 + 数据质量框架 │
                           └────────────────┬────────────────────────┘
                                           │
                    ┌──────────────────────┬┴──────────────────────┐
                    │                      │                       │
          ┌─────────▼──────────┐ ┌─────────▼──────────┐ ┌─────────▼──────────┐
          │  WS-1: 核心数据改造  │ │  WS-2: 新数据接入   │ │  WS-3: 质量保障     │
          │  时间列标准化        │ │  daily_basic       │ │  跨源校验           │
          │  hypertable落地     │ │  stock_st          │ │  数据完整性检查      │
          │  moneyflow/top_list │ │  broker_forecast   │ │  告警与监控         │
          │  pro_bar统一行情    │ │  chip_performance  │ │  回填工具           │
          │                    │ │  chip_distribution │ │  时序健康检查        │
          │                    │ │  technical_factors │ │                    │
          └─────────┬──────────┘ └─────────┬──────────┘ └─────────┬──────────┘
                    │                      │                       │
                    └──────────────────────┼───────────────────────┘
                                           │
                           ┌───────────────▼───────────────────────┐
                           │       WS-4: 服务层接入 (后置)           │
                           │  API暴露 + 筛选条件集成 + 前端展示      │
                           └───────────────────────────────────────┘
```

### 4.2 Vibe-coding 执行原则

1. **一次迁移到位**: 直接把核心事实表统一到标准时间列和 hypertable 形态,不再维护运行时双写、双读、兼容兜底逻辑。
2. **脚本退场**: `scripts/init_timescaledb.py`、`scripts/convert_to_hypertable.py` 视为历史过渡资产,最终由 Alembic migration 和可重复执行的 schema 初始化流程替代。
3. **并行但不抢写**: 每个 Agent 只拥有明确文件/模块边界,避免多人同时修改同一批 migration、model、task 文件。
4. **先收敛口径再接新表**: 先统一 `trade_date_dt`/`created_at` 等时间列规范,再批量扩展新接口和聚合能力。
5. **先事实表后展示层**: 优先完成 `daily_bars`、`moneyflow`、`indicators`、`patterns` 等核心事实表的时序化,前端和 API 改动放在后续工作流。

### 4.3 WS-0: 基础设施层 (前置条件, 约2天)

> **目标**: 为后续所有工作流提供 DB迁移、Timescale 规范、通用行情入口、数据质量框架

| Task ID | 任务 | 交付物 | 依赖 |
|---------|------|--------|------|
| WS0-01 | 引入 Alembic 迁移框架 | `alembic/`, `alembic.ini`, 首次 auto-generate | 无 |
| WS0-02 | 定义时间列与唯一约束规范 | 统一 `DATE/TIMESTAMP` 字段、事实表唯一键、索引命名约定 | 无 |
| WS0-03 | 定义 Timescale 落地规范 | hypertable 范围、chunk 策略、compression/retention 基线、连续聚合候选清单 | WS0-02 |
| WS0-04 | 实现通用行情抽象 `TushareProvider.fetch_pro_bar()` | 支持 asset=E/I/FT/O/FD | 无 |
| WS0-05 | 数据质量基础框架 | `core/quality/validator.py`: 空值率检查、数值范围校验、行数预期校验 | 无 |
| WS0-06 | 积分检测工具 | `scripts/check_tushare_points.py`: 检查当前积分，输出可用接口列表 | 无 |

**WS0-01、WS0-02、WS0-04、WS0-05、WS0-06 可并行。WS0-03 在 WS0-02 完成后启动。**

### 4.4 WS-1: 核心数据改造 (约4天)

> **目标**: 改造现有表结构，完成核心事实表时序化，统一行情获取路径，保留全部字段

| Task ID | 任务 | 交付物 | 依赖 |
|---------|------|--------|------|
| WS1-01 | `stocks` 表补全字段 | Alembic migration + model更新 + `stock_basic` 全字段入库 | WS0-01 |
| WS1-02 | 核心事实表时间列标准化 | `daily_bars`/`fund_flows`/`indicators`/`patterns` 统一使用标准时间列并清理旧字符串主时间列依赖 | WS0-01, WS0-02 |
| WS1-03 | 核心事实表转 hypertable | `daily_bars`、`moneyflow`、`indicators`、`patterns` 完成 hypertable migration | WS1-02, WS0-03 |
| WS1-04 | `fund_flows` → `moneyflow` 表替换 | 新表 DDL + 数据迁移 + `moneyflow` 接口对接 + 直接按 hypertable 设计落表 | WS0-01, WS0-02, WS0-03 |
| WS1-05 | `stock_tops` → `top_list` 表替换 | 新表 DDL + `top_list` 接口全字段对接 | WS0-01 |
| WS1-06 | `daily_bars` 统一走 `pro_bar` | 重构 `fetch_daily_task.py` 使用 `fetch_pro_bar(asset="E")` | WS0-04, WS1-02 |
| WS1-07 | 指数数据入库 | `pro_bar(asset="I")` + daily_bars 表 `asset_type` 字段 | WS0-04, WS1-06 |
| WS1-08 | Timescale 运维基线落地 | compression policy、retention policy、连续聚合候选 SQL、旧脚本退役说明 | WS1-03, WS1-04 |
| WS1-09 | 更新市场下游服务 | `market_data_service.py`, `fund_flow_service.py` 适配新表与标准时间列 | WS1-04, WS1-05, WS1-06 |

**WS1-01、WS1-05 可与 WS1-02 并行。WS1-03 与 WS1-04 可在 WS1-02 / WS0-03 完成后并行。WS1-06 在 WS1-02 完成后启动。WS1-08 在核心 hypertable 完成后推进。**

### 4.5 WS-2: 新数据接入 (约4天)

> **目标**: 集成6个新Tushare接口，每个接口独立成表和获取任务

| Task ID | 任务 | Tushare接口 | 表名 | 依赖 |
|---------|------|------------|------|------|
| WS2-01 | 每日指标接入 | `daily_basic` | `daily_basic` | WS0-01 |
| WS2-02 | ST股票列表接入 | `stock_st` | `stock_st` | WS0-01 |
| WS2-03 | 券商盈利预测接入 | `report_rc` | `broker_forecast` | WS0-01 |
| WS2-04 | 筹码胜率接入 | `cyq_perf` | `chip_performance` | WS0-01 |
| WS2-05 | 筹码分布接入 | `cyq_chips` | `chip_distribution` | WS0-01 |
| WS2-06 | 技术面因子接入 | `stk_factor_pro` | `technical_factors` | WS0-01 |

**每个任务的交付物 (标准模板):**
1. SQLAlchemy Model (`app/models/`)
2. Alembic migration
3. Tushare 获取函数 (`core/crawling/tushare_provider.py`)
4. 调度任务 (`app/jobs/tasks/fetch_xxx_task.py`)
5. 单元测试 (mock Tushare 返回 + 入库验证)

**WS2-01 ~ WS2-06 全部可并行开发，互不依赖。** 新表若具备明确时间轴和滚动保留诉求，建表时直接按 WS0-03 规范决定是否落 hypertable。

### 4.6 WS-3: 数据质量保障 (约2天)

> **目标**: 建立数据质量检查、跨源校验、告警机制，并对 Timescale 落地结果做健康验证

| Task ID | 任务 | 交付物 | 依赖 |
|---------|------|--------|------|
| WS3-01 | 数据完整性检查 | 检查每日各表数据行数是否符合预期 (股票数 vs 实际入库数) | WS0-05 |
| WS3-02 | 数值范围校验 | 价格>=0, 涨跌幅 [-20%, +20%] (含北交所30%), 成交量>=0 | WS0-05 |
| WS3-03 | 跨源一致性校验 | Tushare vs EastMoney 收盘价/成交量抽样比对 | WS0-05 |
| WS3-04 | 数据缺失告警 | 交易日无数据时发送告警 (log + 可选webhook) | WS3-01 |
| WS3-05 | 历史数据回填工具 | `scripts/backfill.py`: 按日期范围+接口批量回填 | WS0-01 |
| WS3-06 | 时序健康检查 | 校验 hypertable、chunk、compression、retention 配置与查询计划符合预期 | WS1-08 |

**WS3-01 ~ WS3-03 可并行。WS3-04 基于 WS3-01。WS3-05 独立。WS3-06 在核心时序表落地后执行。**

### 4.7 WS-4: 服务层接入 (约3天)

> **目标**: 将新数据通过 API 暴露，集成到筛选和策略引擎

| Task ID | 任务 | 交付物 | 依赖 |
|---------|------|--------|------|
| WS4-01 | 新表 Repository 层 | `daily_basic_repo`, `chip_repo`, `tech_factor_repo` 等 | WS-2完成 |
| WS4-02 | 新增 API 端点 | `/api/v1/stocks/{ts_code}/daily-basic`, `/chips`, `/tech-factors` 等 | WS4-01 |
| WS4-03 | 基本面筛选条件集成 | SelectionEngine 支持 PE/PB/PS/市值/换手率 筛选 | WS4-01 |
| WS4-04 | ST股票过滤 | 全局筛选和策略引擎排除 ST 股票选项 | WS2-02 |
| WS4-05 | 券商评级展示 | StockDetail 页面集成分析师评级和目标价 | WS2-03, WS4-02 |
| WS4-06 | 筹码分析展示 | StockDetail 页面集成筹码分布可视化 | WS2-04, WS2-05, WS4-02 |

---

## 五、并行开发分配建议

### 人/Agent 并行模型

| 角色 | 职责 | 任务分配 |
|------|------|----------|
| **Agent A (Schema Owner)** | 迁移框架 + 时间列规范 + Timescale 规范 | WS0-01, WS0-02, WS0-03, WS1-02, WS1-03, WS1-08 |
| **Agent B (Ingestion Owner)** | 通用行情 + 抓取任务收敛 | WS0-04, WS1-06, WS1-07, WS1-09 |
| **Agent C (Core Table Owner)** | 现有核心表重构 | WS1-01, WS1-04, WS1-05 |
| **Agent D (New Facts Owner)** | 日频新增事实表 | WS2-01, WS2-02, WS2-03 |
| **Agent E (Advanced Facts Owner)** | 筹码 + 技术因子 + 时序适配 | WS2-04, WS2-05, WS2-06 |
| **Agent F (Quality Owner)** | 质量校验 + 回填 + 时序健康检查 | WS0-05, WS3-01 ~ WS3-06 |
| **人工 (架构决策)** | 拍板时间列规范、确认 Timescale 策略、做最终 Review | 评审 WS0-03、确认 WS1-08、决定连续聚合范围 |

### 多 Agent 协作方式

1. Agent A 先产出时间列规范和 migration 边界,其它 Agent 才开写各自表和任务。
2. Agent B 只改 provider / task / repository 流程,不改 migration 文件。
3. Agent C/D/E 各自拥有独立表集,禁止跨表“顺手修改”别人负责的 schema。
4. Agent F 不写业务抓取逻辑,专注校验、回填和验收脚本。
5. 所有 Agent 默认按最终目标态编码,不加兼容旧脚本的运行时分支。

### 时间线 (理想并行)

```
Day 1:  ║ WS0-01 ║ WS0-02 ║ WS0-04 ║ WS0-05 ║ WS0-06 ║                ← 先把规范和骨架铺平
        ╠════════╩════════╩════════╩════════╩════════╣
Day 2:  ║ WS0-03 ║ WS1-01 ║ WS1-02 ║ WS2-01~06 (启动)                   ← 规范确定后全面并行
Day 3:  ║ WS1-03 ║ WS1-04 ║ WS1-05 ║ WS1-06 ║ WS3-01~03 ║               ← 核心事实表 + 质量并行
Day 4:  ║ WS1-07 ║ WS1-08 ║ WS2 收尾 ║ WS3-04~06 ║                      ← Timescale 策略与验收闭环
Day 5:  ║ WS1-09 ║ WS4-01~06 ║ 集成测试 ║                                 ← 服务层适配
Day 6:  ║ 查询压测 ║ 文档更新 ║ 部署 ║                                     ← 交付
```

---

## 六、风险与缓解措施

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Tushare 积分不足 (筹码、技术因子需5000+) | 高 | WS2-04~06 无法接入 | WS0-06 首先检查积分，不足则调整优先级 |
| 时间列口径不统一 | 高 | hypertable 无法稳定落地，查询和唯一约束会持续分裂 | 先完成 WS0-02，所有事实表统一按标准时间列设计后再进入 WS1-03 |
| 大表迁移影响已有数据 | 中 | `fund_flows` → `moneyflow`、核心事实表重建可能延长切换窗口 | 迁移前做数据库快照，迁移脚本只保留最终目标态，不引入双写双读 |
| 接口频率限制导致获取慢 | 中 | 全市场筹码数据量大 (5000股 × 每股一次请求) | 分批获取 + 合理 sleep + 按活跃度优先 |
| Timescale 策略配置不当 | 中 | chunk/compression 失配导致写入或查询性能下降 | 在 WS3-06 中补查询计划与 chunk 健康检查，再决定连续聚合范围 |
| `stk_factor_pro` 字段过多 (210+) | 低 | 表宽度大，查询性能可能下降 | 先完整入库，服务层只暴露常用子集，后续按使用情况决定是否拆分 |

---

## 七、验收标准

### Phase 完成定义

- [ ] 所有10个 Tushare 接口已对接并可自动调度
- [ ] 每个新表有对应的 Model + Migration + Fetch Task + Unit Test
- [ ] stocks 表包含 stock_basic 全字段
- [ ] moneyflow 表包含买卖量细分 (大单/中单/小单/超大单)
- [ ] `daily_bars` / `moneyflow` / `indicators` / `patterns` 已统一标准时间列
- [ ] 核心事实表已完成 hypertable 落地，并配置 compression / retention 基线
- [ ] 通用行情接口支持 asset=E/I 获取
- [ ] 数据质量检查覆盖: 完整性 + 范围 + 跨源一致性
- [ ] 时序健康检查覆盖: hypertable / chunk / compression / retention / 查询计划
- [ ] 历史数据回填工具可按日期范围运行
- [ ] 新数据通过 API 端点可访问
- [ ] 筛选引擎支持 PE/PB/换手率/市值 等基本面条件
- [ ] ST 股票可在筛选中被过滤
