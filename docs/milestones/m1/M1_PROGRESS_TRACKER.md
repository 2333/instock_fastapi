# M1 进度跟踪（Phase 1.5 数据层底座）

> 更新频率: 每个任务状态变更时刷新
> 状态取值: `todo` / `in_progress` / `done` / `blocked`

---

## 总览

| Workstream | 负责人 | 总体进度 | 预计完成 |
|------------|--------|----------|---------|
| WS-0 基础设施 | Agent A | ⏳ 未启动 | - |
| WS-1 核心改造 | Agent C | ⏳ 未启动 | - |
| WS-2 新接口接入 | Agent D | ⏳ 未启动 | - |
| WS-3 质量保障 | Agent F | ⏳ 未启动 | - |

**前置条件**:
- [ ] M0 PR #8 已合入 `main`
- [ ] Tushare 积分确认（≥3000+ 基础，≥8000+ 进阶）
- [ ] TimescaleDB 扩展已安装（开发/生产环境）

---

## WS-0 基础设施层

| Task | 负责人 | 状态 | 开始日期 | 完成日期 | 交付物 | 阻塞 |
|------|--------|------|---------|---------|--------|------|
| WS0-01 Alembic 基线 | Agent A | `todo` | - | - | `alembic/`, `run_migrations()` | 无 |
| WS0-02 时间列规范 | Agent A | `todo` | - | - | Model 更新 + 迁移脚本 | WS0-01 |
| WS0-03 Timescale 规范 | Agent A | `todo` | - | - | `TIMESCALE_POLICY.md` + 迁移 | WS0-02 |
| WS0-04 pro_bar 抽象 | Agent B | `todo` | - | - | `pro_bar.py` + 测试 | 无 |
| WS0-05 质量框架骨架 | Agent F | `todo` | - | - | `data_quality.py` + CLI | 无 |

**WS-0 完成标志**: 所有任务 `done` → 解锁 WS-1 与 WS-2

---

## WS-1 核心改造层

| Task | 负责人 | 状态 | 依赖 | 交付物 | 备注 |
|------|--------|------|------|--------|------|
| WS1-10 stocks 补全字段 | Agent C | `todo` | WS0-02 | 迁移 + model 更新 | 补全 10+ 字段 |
| WS1-11 daily_bars 时间列标准化 | Agent C | `todo` | WS0-02 | 迁移（数据转换） | trade_date → trade_date_dt |
| WS1-12 daily_bars hypertable | Agent C | `todo` | WS0-03 | 迁移（Timescale） | chunk 7d, compression 30d |
| WS1-13 moneyflow 替换 fund_flows | Agent C | `todo` | WS0-02 | 新表 + 写入切换 | 17 个细分字段 |
| WS1-14 top_list 替换 stock_tops | Agent C | `todo` | WS0-02 | 新表 + 写入切换 | 龙虎榜 |
| WS1-15 indicators/patterns 迁移 | Agent C | `todo` | WS0-02/03 | 时间列 + hypertable | 技术指标 + 形态 |
| WS1-16 pro_bar 切换主抓取 | Agent B | `todo` | WS0-04 | fetch_daily_task 改造 | 统一行情入口 |

**WS-1 完成标志**: 所有核心表改造完成，主抓取任务切换到 pro_bar

---

## WS-2 新接口接入（全部并行）

| 接口 | 表名 | 负责人 | 状态 | 交付物 | 积分要求 | 备注 |
|------|------|--------|------|--------|---------|------|
| daily_basic | daily_basic | Agent D | `todo` | Model + Migration + Provider + Test | 2000+ | 换手率/PE/PB/市值 |
| stock_st | stock_st | Agent D | `todo` | Model + Migration + Provider + Test | 3000+ | ST 标记 |
| broker_forecast | broker_forecast | Agent D | `todo` | Model + Migration + Provider + Test | 8000+ | 券商预测 |
| chip_performance | chip_performance | Agent D | `todo` | Model + Migration + Provider + Test | 5000+ | 筹码胜率 |
| chip_distribution | chip_distribution | Agent D | `todo` | Model + Migration + Provider + Test | 5000+ | 筹码分布 |
| technical_factors | technical_factors | Agent D | `todo` | Model + Migration + Provider + Test | 5000+ | 210+ 因子 |

**WS-2 完成标志**: 所有接口模型、迁移、抓取任务、测试完成

---

## WS-3 质量保障层

| Task | 负责人 | 状态 | 依赖 | 交付物 | 说明 |
|------|--------|------|------|--------|------|
| WS3-31 完整性检查 | Agent F | `todo` | WS1-04/WS2 | 检查脚本 + 阈值配置 | 行数 vs 基准 |
| WS3-32 范围校验 | Agent F | `todo` | WS1-04/WS2 | 日期/代码覆盖报告 | 起始日期、连续性 |
| WS3-33 跨源一致性 | Agent F | `todo` | WS1-04/WS2 | 对比脚本 + 容差 | Tushare vs EastMoney |
| WS3-34 告警与监控 | Agent F | `todo` | WS3-31 | 告警规则 + 通知集成 | 失败率 >5% 告警 |
| WS3-35 回填工具 | Agent F | `todo` | WS1-04/WS2 | `scripts/backfill.py` | 按日期范围回填 |
| WS3-36 时序健康检查 | Agent F | `todo` | WS0-03 | 健康检查脚本 + 报告 | hypertable/chunk/compression |

**WS-3 完成标志**: 质量体系就绪，可支撑 M1 验收

---

## M1 整体验收清单

- [ ] WS-0 全部任务 done（基础设施就绪）
- [ ] WS-1 核心改造完成（表结构统一、hypertable 落地、抓取切换）
- [ ] WS-2 新接口全部接入（6 张表可查询）
- [ ] WS-3 质量检查体系运行（至少 1 次回填演练留痕）
- [ ] API 端点可访问新表数据
- [ ] 筛选引擎支持 PE/PB/换手率/市值等基本面条件（如适用）
- [ ] 测试覆盖新增模块

---

## 阻塞与风险记录

| 阻塞项 | 影响任务 | 解决状态 | 备注 |
|--------|---------|---------|------|
| M0 PR #8 未合并 | 全部 | ⏳ 等待 | 关键路径 |
| Tushare 积分不足 | WS-2 部分接口 | ❓ 未确认 | 需人工检查 |
| TimescaleDB 未安装 | WS-0/WS-1 | ❓ 未确认 | 环境依赖 |

---

**更新说明**:
- 首次创建: 2026-04-05
- 下次更新: WS-0 启动后每日刷新
