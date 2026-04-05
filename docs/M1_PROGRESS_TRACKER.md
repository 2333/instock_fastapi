# M1 进度跟踪（Phase 1.5 数据层底座）

> 更新频率: 每个任务状态变更时刷新
> 状态取值: `todo` / `in_progress` / `done` / `blocked`
> 任务来源: 29 个可执行任务包（docs/M1_TASK_*.md）

---

## 总览

| Workstream | 负责人 | 总体进度 | 预计完成 |
|------------|--------|----------|---------|
| WS-0 基础设施 | Agent A/B/F | ⏳ 未启动 | 2 天 |
| WS-1 核心改造 | Agent C/D | ⏳ 未启动 | 3 天 |
| WS-2 新接口接入 | Agent E | ⏳ 未启动 | 2 天 |
| WS-3 质量保障 | Agent F | ⏳ 未启动 | 2 天 |

**前置条件**:
- [x] M0 PR #8 已合入 `main` (commit a0a729f)
- [ ] Tushare 积分确认（≥3000+ 基础，≥8000+ 进阶）**← 当前阻塞**
- [x] TimescaleDB 扩展已安装（验证通过）
- [x] Alembic 工具可用 (1.18.4)

---

## WS-0 基础设施层 (5/5 ✅ 就绪)

| Task | 负责人 | 状态 | 开始日期 | 完成日期 | 交付物 | 阻塞 |
|------|--------|------|---------|---------|--------|------|
| WS0-01 Alembic 基线 | Agent A | `todo` | - | - | 迁移脚本 + 配置 | 无 |
| WS0-02 时间列规范 | Agent A | `todo` | - | - | Model + 迁移 + 数据转换 | WS0-01 |
| WS0-03 Timescale 规范 | Agent A | `todo` | - | - | Hypertable + 策略 | WS0-02 |
| WS0-04 pro_bar 抽象 | Agent B | `todo` | - | - | 统一行情接口 | 无 |
| WS0-05 质量框架骨架 | Agent F | `todo` | - | - | QualityEngine + CLI | 无 |

**WS-0 完成标志**: 所有任务 `done` → 解锁 WS-1 与 WS-2

---

## WS-1 核心改造层 (5/12 ✅ 就绪 + 7 待拆解)

| Task | 负责人 | 状态 | 依赖 | 交付物 | 备注 |
|------|--------|------|------|--------|------|
| WS1-01 股票同步 | Agent C | `todo` | WS0-01 | stocks 表 + sync_stocks.py | 主数据表 |
| WS1-02 日线回填 | Agent C | `todo` | WS0-01/02/WS1-01 | backfill + fetch_daily_task | 千万级数据迁移 |
| WS1-03 指标引擎 | Agent D | `todo` | WS1-02 | IndicatorEngine + compute_task | TA-Lib 10+ 指标 |
| WS1-04 分钟线 | Agent C | `todo` | WS0-01/02 | minute_bars + fetch_task | 高频数据 |
| WS1-05 基本面数据 | Agent C | `todo` | WS1-01 | financial_indicators | 财报同步 |
| WS1-06 ~ 12 | - | `todo` | - | - | WS-1 执行期间拆解（7 项） |

**WS-1 完成标志**: 核心表改造完成，主抓取任务切换到 pro_bar

---

## WS-2 新接口扩展层 (6/6 ✅ 就绪)

| Task | 负责人 | 状态 | 依赖 | 交付物 | 积分要求 |
|------|--------|------|------|--------|---------|
| WS2-01 moneyflow | Agent E | `todo` | WS0-01/02/03 | 资金流向表 + 抓取 | 3000+ |
| WS2-02 limit list | Agent E | `todo` | WS0-01/02 | 涨跌停列表 | 3000+ |
| WS2-03 limit detail | Agent E | `todo` | WS2-02 | 涨跌停明细 | 3000+ |
| WS2-04 disclosure | Agent E | `todo` | WS1-01 | 公告数据 | 5000+ |
| WS2-05 bak_basic | Agent E | `todo` | WS1-01 | 历史快照 | 2000+ |
| WS2-06 top_inst | Agent E | `todo` | WS1-01 | 龙虎榜机构 | 5000+ |

**WS-2 完成标志**: 所有新接口接入完成

---

## WS-3 质量保障层 (6/6 ✅ 就绪)

| Task | 负责人 | 状态 | 依赖 | 交付物 | 说明 |
|------|--------|------|------|--------|------|
| WS3-01 completeness | Agent F | `todo` | WS1-02 | 完整性检查（≥99%） | 数据覆盖率 |
| WS3-02 alerting | Agent F | `todo` | WS3-01 | 多通道告警 | webhook/email/钉钉 |
| WS3-03 monitoring | Agent F | `todo` | WS0-05 | 监测增强 | DB/磁盘/Timescale/延迟 |
| WS3-04 lineage | Agent F | `todo` | WS3-01 | 数据血缘追踪 | 全链路图谱 |
| WS3-05 dashboard | Agent F | `todo` | WS3-03 | 监控仪表板 | FastAPI + 可视化 |
| WS3-06 report | Agent F | `todo` | WS3-02/05 | 报告自动化 | 每日邮件 |

**WS-3 完成标志**: 质量体系就绪，可支撑 M1 验收

---

## 执行日志

- 启动时间: _待触发_
- 最近更新: _未开始_
- 执行日志: `logs/m1_execution/execution.log`

---

## 快速命令

```bash
# 检查环境就绪
python scripts/check_m1_readiness.py

# 一键启动 M1
./scripts/start_m1_phase.sh

# 监控进度
python scripts/track_m1_progress.py --watch

# Agent 更新任务状态
python scripts/update_m1_task.py <task_id> <state> --note "备注"
```

---

**最后更新**: _自动生成_ | **数据源**: `docs/M1_PROGRESS_TRACKER.md`
