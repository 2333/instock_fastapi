# M1 启动就绪确认清单

> 版本: 2026-04-05
> 状态: 阻塞中 → 就绪后触发
> 触发条件: `scripts/check_m1_readiness.py` 返回所有 ✅

---

## 就绪前状态（当前）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| TimescaleDB 扩展 | ✅ 已安装 | `SELECT * FROM pg_extension WHERE extname='timescaledb'` |
| 数据库连接 | ✅ 正常 | config tests 通过 |
| Alembic 工具 | ✅ 1.18.4 | `alembic --version` |
| Tushare Token | ❌ **阻塞** | API 返回 40101，token 无效 |

**修复步骤**（用户操作）:
```bash
# 1. 登录 https://tushare.pro 重置 Token
# 2. 更新 .env
sed -i '' "s/^TUSHARE_TOKEN=.*/TUSHARE_TOKEN=你的新token/" .env
# 3. 验证
python scripts/check_m1_readiness.py
```

---

## 就绪后自动执行序列

一旦环境检查全绿，按顺序执行:

### 阶段 1: 代码库状态确认
```bash
cd /Users/zhangkai/projects/instock_fastapi
git checkout main
git pull origin main
git status  # 应显示 clean
```

### 阶段 2: 运行就绪检查
```bash
source .venv/bin/activate
python scripts/check_m1_readiness.py
# 预期: 所有 ✅，输出 "环境就绪，可以启动 M1 WS-0 第一批任务"
```

### 阶段 3: 启动 WS-0 第一批任务（并行/串行）

**任务清单（已准备就绪，可直接分派）**:

| 任务 | 负责人 | 命令/动作 | 预期输出 | 状态 |
|------|--------|-----------|----------|------|
| WS0-01 Alembic 基线 | Agent A | `alembic init alembic/` → 配置 → `alembic revision --autogenerate -m "baseline"` → `alembic upgrade head` | `alembic/` 目录 + 基准迁移脚本 | Ready |
| WS0-02 时间列规范 | Agent A | 修改 Model → `alembic revision --autogenerate -m "standardize-time-columns"` → 分批数据迁移 → `alembic upgrade head` | 迁移脚本 + trade_date_dt 列就绪 | Ready |
| WS0-03 Timescale 规范 | Agent A | 编写 SQL 迁移: `SELECT create_hypertable('daily_bars', 'trade_date_dt')` 等 | hypertable 创建成功 | Ready |
| WS0-04 pro_bar 抽象 | Agent B | 实现 `app/services/pro_bar.py` + 测试 `tests/test_pro_bar.py` | 统一行情接口可用 | Ready |
| WS0-05 质量框架骨架 | Agent F | 创建 `app/services/data_quality.py` + `scripts/run_quality_checks.py` | 框架可运行（占位检查） | Ready |

**详细任务文档**（已创建）:
- `docs/M1_TASK_WS0-01_ALCHEMY.md` - Alembic 基线任务说明书
- `docs/M1_TASK_WS0-02_TIME_COLUMNS.md` - 时间列规范任务说明书
- `docs/M1_TASK_WS0-03_TIMESCALE.md` - Timescale 规范任务说明书（待创建）
- `docs/M1_TASK_WS0-04_PRO_BAR.md` - pro_bar 抽象任务说明书（待创建）
- `docs/M1_TASK_WS0-05_QUALITY.md` - 质量框架任务说明书（待创建）

### 阶段 4: 进度跟踪初始化
```bash
# 更新进度跟踪文档
cat > docs/M1_PROGRESS_TRACKER.md << 'EOF'
# M1 进度跟踪（实时更新）
## WS-0 基础设施层
| Task | 负责人 | 状态 | 开始日期 | 完成日期 |
|------|--------|------|---------|---------|
| WS0-01 | Agent A | in_progress | 2026-04-05 | - |
| WS0-02 | Agent A | todo | - | - |
| WS0-03 | Agent A | todo | - | - |
| WS0-04 | Agent B | todo | - | - |
| WS0-05 | Agent F | todo | - | - |
EOF
```

### 阶段 5: 执行监控
```bash
# 每个任务完成后更新状态
# 使用 sessions_spawn 分派子 Agent（如需并行）
# 每日 heartbeat 检查进度
```

---

## 触发命令（一键启动）

创建 `scripts/start_m1_phase.sh`（待实现）:

```bash
#!/bin/bash
set -e

echo "=== M1 Phase 1.5 启动 ==="

# 1. 检查就绪
echo "检查环境就绪..."
python scripts/check_m1_readiness.py

# 2. 切换到 main 并确保最新
git checkout main
git pull origin main

# 3. 启动 WS-0 任务（可并行分派）
echo "启动 WS-0 第一批任务..."

# 任务 1: Alembic 基线
sessions_spawn --task "docs/M1_TASK_WS0-01_ALCHEMY.md" --agentId agent-a &

# 任务 2: 时间列规范
sessions_spawn --task "docs/M1_TASK_WS0-02_TIME_COLUMNS.md" --agentId agent-a &

# 任务 3: Timescale 规范
sessions_spawn --task "docs/M1_TASK_WS0-03_TIMESCALE.md" --agentId agent-a &

# 任务 4: pro_bar 抽象
sessions_spawn --task "docs/M1_TASK_WS0-04_PRO_BAR.md" --agentId agent-b &

# 任务 5: 质量框架
sessions_spawn --task "docs/M1_TASK_WS0-05_QUALITY.md" --agentId agent-f &

echo "M1 WS-0 任务已全部分派，等待完成..."
```

---

## 验收标准（M1 完成）

- [ ] WS-0 全部 5 项任务 done
- [ ] WS-1 核心改造 7 项完成
- [ ] WS-2 新接口 6 张表全部接入
- [ ] WS-3 质量体系运行并通过至少 1 次回填演练
- [ ] 新增数据可通过 API 访问
- [ ] 测试覆盖新增模块（新增测试 ≥ 对应任务数 50%）
- [ ] 文档更新（DATA_LAYER_REPORT.md 与实现一致）

---

## 快速参考

**环境检查**: `python scripts/check_m1_readiness.py`
**稳定性监测**: `python scripts/monitor_stability.py`
**快速修复**: `QUICKFIX_M1_TUSHARE_TOKEN.md`
**任务拆解**: `docs/M1_TASK_BREAKDOWN.md`
**进度跟踪**: `docs/M1_PROGRESS_TRACKER.md`
**启动清单**: `docs/M1_KICKOFF_CHECKLIST.md`
**就绪总览**: `docs/M1_READINESS_SUMMARY.md`

---

**维护**: 本清单用于 M1 启动时的操作指引，环境就绪后按序执行即可。
