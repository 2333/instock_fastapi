# M1 启动就绪清单（待 Tushare Token 修复后触发）

> 历史说明: 本文档保留为 2026-04-05 的旧启动清单快照。当前重启口径以 `docs/milestones/m1/M1_RESTART_PLAN.md` 为准；本文中引用的 `scripts/check_m1_readiness.py` 已不再保证存在。本文中的 “Tushare token 阻塞 M1 启动” 只代表当日旧口径，不再代表当前阶段 M1 的收口条件。
>
> 状态: 历史快照（旧口径曾要求等待用户更新 `.env` 中的 `TUSHARE_TOKEN`）
> 最后检查: 2026-04-05 08:58（token 仍无效）
> 触发条件: `scripts/check_m1_readiness.py` 返回所有检查 ✅

---

## 历史阻塞记录

| 检查项 | 状态 | 详情 |
|--------|------|------|
| TimescaleDB | ✅ | 扩展已安装 |
| 数据库连接 | ✅ | config tests 通过 |
| Alembic | ✅ | 1.18.4 可用 |
| Tushare Token | ❌ | API 40101 "token 不对" |

**当时的修复任务**（用户手动）:
1. 登录 https://tushare.pro
2. 重置 API Token
3. 更新项目 `.env` 文件：`TUSHARE_TOKEN=你的新token`
4. 重新运行 `python scripts/check_m1_readiness.py` 验证

参考文档: `docs/milestones/m1/M1_TUSHARE_TOKEN_BLOCK.md`

---

## 历史就绪触发流程（自动）

一旦环境检查通过，按顺序自动执行：

### 阶段 1：M0 合并确认
- [ ] PR #8 已合入 `main`
- [ ] 本地 `main` 分支已拉取最新

### 阶段 2：WS-0 第一批任务启动（并行/串行）

| 任务 | 负责人 | 命令/动作 | 预期输出 |
|------|--------|-----------|----------|
| WS0-01 Alembic 基线 | Agent A | `alembic init alembic/` + 配置 | `alembic/` 目录 |
| WS0-02 时间列规范 | Agent A | `alembic revision --autogenerate -m "standardize-time-columns"` | 迁移脚本 |
| WS0-03 Timescale 规范 | Agent A | 编写 hypertable 创建迁移 | `SELECT * FROM timescaledb_information.hypertables` 可查询 |
| WS0-04 pro_bar 抽象 | Agent B | 实现 `app/services/pro_bar.py` | 测试 `tests/test_pro_bar.py` 通过 |
| WS0-05 质量框架骨架 | Agent F | 创建 `app/services/data_quality.py` | `scripts/run_quality_checks.py` 可运行 |

**总预计时间**: 2 天（含并行）

### 阶段 3：进度跟踪初始化
- [ ] 创建 `docs/milestones/m1/M1_PROGRESS_TRACKER.md`（如尚未创建）
- [ ] 将所有 WS-0 任务状态改为 `in_progress`
- [ ] 记录开始日期与负责人

---

## 历史快速启动命令（旧口径）

```bash
# 1. 确认在 main 分支且最新
git checkout main
git pull origin main

# 2. 运行环境检查（应全绿）
python scripts/check_m1_readiness.py

# 3. 启动 WS-0 第一批任务（示例：Alembic 基线）
# 由 Agent A 执行：
cd /Users/zhangkai/projects/instock_fastapi
alembic init alembic/
# 编辑 alembic.ini 与 env.py 配置数据库连接
alembic revision --autogenerate -m "baseline"
alembic upgrade head
```

---

## 历史验收标准（旧版 M1 完成口径）

- [ ] WS-0 全部 5 项任务 done
- [ ] WS-1 核心改造 7 项完成
- [ ] WS-2 新接口 6 张表全部接入
- [ ] WS-3 质量体系运行并通过至少 1 次回填演练
- [ ] 新增数据可通过 API 访问
- [ ] 测试覆盖新增模块

---

**历史 heartbeat 检查建议**:
- 重新运行 `scripts/check_m1_readiness.py`
- 如 Tushare 变为 ✅，立即汇报并触发 M1 启动序列
- 如仍 ❌，继续等待用户操作，不重复已提供的修复指南
