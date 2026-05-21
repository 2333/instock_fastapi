# InStock 系统架构

更新时间：2026-05-20

适用范围：当前 `main` 分支，`0.4.1+` 运行形态。

## 1. 概览

InStock 是一个面向 A 股数据分析、筛选、回测和提醒的单体应用。当前架构保持为一个 FastAPI 后端、一个 Vue 3 前端、一个 PostgreSQL/TimescaleDB 数据库，以及由 APScheduler 驱动的盘后数据任务。生产部署使用已构建镜像，数据库由部署 compose 外部管理；release staging 使用同 tag 镜像验证生产工件。

当前系统的核心原则：

- `Saved Screener` 是用户编写筛选条件的唯一事实源。
- `Alert Subscription` 只绑定筛选条件版本和投递配置，不复制筛选定义。
- `AlertRun / AlertRunHit / Notification` 是执行历史和投递记录，不反向充当配置。
- 市场数据任务和告警任务都以 readiness 为门禁；数据不完整时跳过，而不是降级到上一交易日。
- `core/` 提供采集、指标、形态、策略和回测能力；`app/` 负责 HTTP、服务编排、数据库模型和调度。

## 2. 系统上下文图

```mermaid
flowchart TB
    user["用户 / 浏览器"]
    frontend["Vue 3 前端\nNginx 静态服务"]
    api["FastAPI 后端\nRouters / Services / Scheduler"]
    db[("PostgreSQL + TimescaleDB\n业务数据 + 时序数据 + 执行历史")]
    logs[("app_logs volume\n运行日志")]

    eastmoney["东方财富"]
    tushare["Tushare HTTP API"]
    baostock["BaoStock"]

    scripts["运维脚本\nbackup / restore / smoke / deploy"]
    alembic["Alembic migrations"]

    user --> frontend
    frontend -->|"REST /api/v1"| api
    api -->|"SQLAlchemy asyncpg"| db
    api --> logs

    api -->|"行情 / 资金流 / 参考数据"| eastmoney
    api -->|"基础事实 / 板块资金 / 参考数据"| tushare
    api -->|"日线 / 复权 / 股票主数据"| baostock

    scripts --> api
    scripts --> db
    alembic --> db
```

## 3. 运行时分层图

```mermaid
flowchart TB
    subgraph web["web/ 前端层"]
        views["Views\nDashboard / Stocks / Selection / Backtest / Attention"]
        router["Vue Router"]
        apiClient["Axios API client"]
        store["Pinia state"]
    end

    subgraph app["app/ 后端应用层"]
        middleware["Middleware\nCORS / request logging / exception handler"]
        routers["API Routers\nstock / etf / facts / indicators / patterns / market"]
        userRouters["Auth & User Routers\nauth / attention / events"]
        alertRouters["Screening & Alert Routers\nselection / alerts / notifications"]
        services["Services\n业务编排与事务边界"]
        repositories["Repositories\n查询封装"]
        models["SQLAlchemy Models\nusers / stocks / facts / alerts / backtests"]
        scheduler["APScheduler\nmarket jobs / post-close alerts / missed-run recovery"]
    end

    subgraph core["core/ 领域能力层"]
        crawlers["Data Providers\nEastMoney / Tushare / BaoStock"]
        indicators["Indicator Calculator\nTA-Lib / pandas"]
        patterns["Pattern Recognizer"]
        strategy["Strategy Engine"]
        backtest["Backtest Engine"]
    end

    db[("PostgreSQL + TimescaleDB")]

    views --> router
    views --> store
    store --> apiClient
    apiClient --> routers
    apiClient --> userRouters
    apiClient --> alertRouters

    routers --> middleware
    userRouters --> middleware
    alertRouters --> middleware
    middleware --> services
    services --> repositories
    services --> models
    repositories --> models
    models --> db

    scheduler --> services
    services --> crawlers
    services --> indicators
    services --> patterns
    services --> strategy
    services --> backtest
    crawlers --> db
    indicators --> db
    patterns --> db
    strategy --> db
    backtest --> db
```

## 4. 数据与任务流

```mermaid
flowchart LR
    subgraph sources["外部数据源"]
        eastmoney["东方财富"]
        tushare["Tushare"]
        baostock["BaoStock"]
    end

    subgraph jobs["APScheduler 盘后任务"]
        universe["17:35 股票主数据"]
        daily["17:40 日线数据"]
        classification["周一 17:50 股票分类"]
        fund["16:00 资金流"]
        indicators["19:10 技术指标"]
        patterns["19:40 形态识别"]
        strategy["20:10 策略选股"]
        alerts["20:25 订阅提醒"]
        reference["21:45 龙虎榜 / 大宗交易"]
        cleanup["周日 03:00 清理"]
        recovery["startup missed-run recovery"]
    end

    subgraph tables["主要数据表"]
        stocks[("stocks")]
        dailyBars[("daily_bars")]
        facts[("daily_basic / stock_st / technical_factors")]
        fundFlows[("fund_flows / sector_fund_flows")]
        patternsTable[("patterns")]
        strategyResults[("strategy_results")]
        selection[("selection_conditions / selection_results")]
        alertsTables[("alert_subscriptions / alert_runs / alert_run_hits / notifications")]
        marketRef[("stock_tops / stock_block_trades / north_bound_funds")]
    end

    sources --> universe
    sources --> daily
    sources --> classification
    sources --> fund
    sources --> reference

    universe --> stocks
    classification --> stocks
    daily --> dailyBars
    daily --> facts
    fund --> fundFlows
    reference --> marketRef

    dailyBars --> indicators
    facts --> indicators
    indicators --> facts
    dailyBars --> patterns
    facts --> patterns
    patterns --> patternsTable

    patternsTable --> strategy
    facts --> strategy
    strategy --> strategyResults

    selection --> alerts
    dailyBars --> alerts
    facts --> alerts
    patternsTable --> alerts
    alerts --> alertsTables

    dailyBars --> recovery
    fundFlows --> recovery
    marketRef --> recovery
    recovery --> jobs

    cleanup --> tables
```

### Readiness 门禁

市场与提醒任务共享一条保守约束：当目标交易日缺少 `daily_bars` 或 active universe 存在 partial gap 时，任务必须跳过。订阅提醒不会因为数据缺口回退到上一交易日，也不会在不完整 universe 上产生通知。

## 5. 筛选与订阅提醒架构

```mermaid
flowchart TB
    screener["Saved Screener\nselection_conditions\n用户编写的事实源"]
    subscription["Alert Subscription\nalert_subscriptions\n绑定 screener id/version/hash"]
    registry["Screener Registry\n字段目录 / 参数 schema / UI metadata"]
    adapter["Evaluator Adapter\n当前 SQL + TA-Lib\n未来可替换为 vbtpro"]
    runtime["Selection Runtime\n执行筛选并返回命中集合"]
    run["AlertRun\n执行快照 / 状态 / definition_snapshot"]
    hit["AlertRunHit\n命中股票明细"]
    notification["Notification\n用户消息 / dedupe_key / payload"]
    readiness["Readiness Gate\nlatest trade_date / daily_bars coverage"]

    screener --> subscription
    subscription --> readiness
    readiness -->|"ready"| registry
    readiness -->|"not ready: skipped"| run
    registry --> adapter
    adapter --> runtime
    runtime --> run
    runtime --> hit
    run --> notification
    hit --> notification
```

运行约束：

- 手动触发和盘后调度都进入 `AlertSubscriptionService.run_subscription()`。
- 同一订阅、同一交易日通过执行记录和通知 `dedupe_key` 去重。
- 修改 `Saved Screener` 后，订阅进入 stale 状态；再次运行必须先显式刷新绑定版本。
- startup missed-run checker 只补 latest trade date 的缺失 run，不承担历史 backfill。

## 6. 部署架构

```mermaid
flowchart TB
    subgraph prod["Production: docker-compose.deploy.yml"]
        prodFront["instock_frontend\ninstock/instock-frontend:APP_VERSION\nhost 3001 -> container 80"]
        prodApp["instock_app\ninstock/instock-app:APP_VERSION\nhost 8000 -> container 8000"]
        prodDb[("external instock_postgres\nPostgreSQL + TimescaleDB\ninstock_network")]
        prodLogs[("external instock_fastapi_app_logs")]
        prodFront --> prodApp
        prodApp --> prodDb
        prodApp --> prodLogs
    end

    subgraph staging["Release Staging: docker-compose.staging.release.yml"]
        stageFront["instock_staging_frontend\nsame release image tag\nhost 3003 -> container 80"]
        stageApp["instock_staging_app\nsame release image tag\nhost 8002 -> container 8000"]
        stageDb[("instock_staging_postgres\nTimescaleDB\nhost 5434 by default")]
        stageFront --> stageApp
        stageApp --> stageDb
    end

    subgraph dev["Development: docker-compose.dev.yml"]
        devFront["instock_dev_frontend\nbuild from web/\nhost 3002 -> container 80"]
        devApp["instock_dev_app\nbind-mounted app/core/scripts/config\nhost 8001 -> container 8000"]
        devDb[("instock_dev_postgres\nTimescaleDB\nhost 5433 -> container 5432")]
        devFront --> devApp
        devApp --> devDb
    end
```

部署边界：

- 生产 compose 只管理 app/frontend 容器和 app 日志 volume，不创建生产数据库。
- release staging 使用和生产相同的镜像 tag，适合合并后验证迁移、健康、API 合同、scheduler/readiness 和 smoke。
- dev compose 使用 bind mount，适合日常开发，不应作为 release artifact 的最终证据。
- 当前 compose 文件没有启用 Redis、Prometheus 或 Grafana；`core/storage/redis.py` 是可选能力，不是默认运行依赖。

## 7. 主要数据库域

```mermaid
erDiagram
    users ||--o{ user_settings : owns
    users ||--o{ user_events : emits
    users ||--o{ attention : watches
    users ||--o{ selection_conditions : authors
    users ||--o{ alert_subscriptions : owns
    users ||--o{ notifications : receives

    stocks ||--o{ daily_bars : has
    stocks ||--o{ indicators : has
    stocks ||--o{ patterns : has
    stocks ||--o{ fund_flows : has

    selection_conditions ||--o{ selection_results : produces
    selection_conditions ||--o{ alert_subscriptions : bound_by
    alert_subscriptions ||--o{ alert_runs : executes
    alert_runs ||--o{ alert_run_hits : records
    alert_runs ||--o{ notifications : emits

    strategies ||--o{ strategy_results : produces
    backtest_tasks ||--o{ backtest_results : stores
```

重要表组：

- 用户与行为：`users`、`user_settings`、`user_events`、`attention`。
- 市场主数据与事实：`stocks`、`daily_bars`、`daily_basic`、`stock_st`、`technical_factors`。
- 分析结果：`indicators`、`patterns`、`strategy_results`、`selection_results`。
- 筛选与提醒：`selection_conditions`、`alert_subscriptions`、`alert_runs`、`alert_run_hits`、`notifications`。
- 市场参考：`stock_tops`、`stock_block_trades`、`stock_bonus`、`stock_limitup_reasons`、`sector_fund_flows`、`north_bound_funds`。
- 回测：`strategies`、`backtest_tasks`、`backtest_results`。

## 8. 技术栈

| 层级 | 当前技术 |
| --- | --- |
| 前端 | Vue 3, TypeScript, Vite, Pinia, Vue Router, Axios, ECharts, Element Plus |
| 后端 API | Python 3.11+, FastAPI, Pydantic Settings, SQLAlchemy 2.x async, asyncpg |
| 任务调度 | APScheduler, startup missed-run recovery, single-process file lock |
| 数据库 | PostgreSQL + TimescaleDB, Alembic migrations |
| 数据与计算 | pandas, NumPy, TA-Lib, EastMoney/Tushare/BaoStock providers |
| 部署 | Docker, Docker Compose, Nginx static frontend image |
| 验证 | pytest, ruff, black, vue-tsc, vite build, smoke scripts, compose config checks |

## 9. 代码位置速查

| 能力 | 主要位置 |
| --- | --- |
| FastAPI 入口与 router 注册 | `app/main.py` |
| API 路由 | `app/api/routers/` |
| 服务层 | `app/services/` |
| 数据模型 | `app/models/stock_model.py` |
| 数据访问封装 | `app/repositories/` |
| 定时任务 | `app/jobs/scheduler.py`, `app/jobs/tasks/` |
| 采集、指标、形态、策略、回测核心 | `core/` |
| 前端应用 | `web/` |
| 迁移 | `alembic/versions/` |
| 环境编排 | `docker-compose.dev.yml`, `docker-compose.staging.release.yml`, `docker-compose.deploy.yml` |
| 发布验证脚本 | `scripts/smoke_api_contracts.py`, `scripts/deploy_release.sh` |
