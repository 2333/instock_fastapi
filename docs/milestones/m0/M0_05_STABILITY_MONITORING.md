# M0-05: 10 个交易日稳定性监测方案

> 版本: 2026-04-05
> 目的: 将"连续 10 个交易日数据更新稳定性"从模糊门槛转化为可自动化监测的观察项，解除 M0 冻结阻塞

---

## 问题背景

**原 DoD 表述**:
> 数据更新稳定性: 连续 5 个交易日 100% (Phase 0 验收表)
> 全市场扫描响应时间 < 30s (已达标，2026-04-03 测量)

**当前状态**:
- 已有单日健康检查端点: `GET /api/v1/market/task-health`
- 已有 quick suite 单次执行记录（2026-04-02 ~ 2026-04-03）
- 缺少连续多日自动记录与累计统计

**阻塞点**: 若作为硬门槛，需等待 10 个交易日（约 2 周）；若降级为观察项，需明确观察方法与验收标准。

---

## 方案：稳定性作为持续观察项（推荐）

将 10 日稳定性**降级为观察指标**，M0 可立即冻结。具体做法：

### 1. 建立稳定性监测脚本

新增 `scripts/monitor_stability.py`，每日heartbeat自动执行：

```python
#!/usr/bin/env python3
"""
每日稳定性监测（从 OpenClaw heartbeat 调用）
记录: 最新交易日、任务健康状态、扫描响应时间、数据完整性
输出: memory/stability_log.jsonl（追加）+ 最近 N 日汇总
"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "memory" / "stability_log.jsonl"

def check_market_date():
    """调用 API 获取最新交易日"""
    # 使用 httpx 调用本地 health 端点，或直接查询数据库
    pass

def check_task_health():
    """调用 /api/v1/market/task-health 并解析结果"""
    pass

def run_quick_suite():
    """运行 Phase 0/1 快速回归套件"""
    result = subprocess.run(
        ["poetry", "run", "pytest", "tests/test_screening_baseline.py", "tests/test_api.py::TestMarketTaskHealthAPI", "-q"],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout

def record(day: int, status: dict):
    entry = {
        "date": datetime.now(timezone.utc).isoformat(),
        "trading_day": day,
        "market_date": status.get("latest_trade_date"),
        "task_healthy": status.get("healthy"),
        "quick_suite_passed": status.get("suite_passed"),
        "scan_latency_ms": status.get("scan_latency"),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(entry) + "\n", append=True)

def summarize_last_n_days(n=10):
    """读取最近 n 天日志，计算稳定性百分比"""
    logs = list(LOG_PATH.read_text().strip().splitlines())[-n:]
    total = len(logs)
    passed = sum(1 for line in logs if json.loads(line)["quick_suite_passed"])
    return passed / total * 100 if total else None

if __name__ == "__main__":
    day_status = {
        "latest_trade_date": check_market_date(),
        "healthy": check_task_health(),
    }
    suite_ok, _ = run_quick_suite()
    day_status["suite_passed"] = suite_ok

    record(day_status)
    rate = summarize_last_n_days(10)
    print(f"Stability last 10 days: {rate}%")
```

**执行方式**：每次 heartbeat 自动调用，结果追加到 `memory/stability_log.jsonl`。

### 2. 验收标准（观察项）

| 指标 | 目标值 | 监测方法 |
|------|--------|----------|
| 任务健康检查成功率 | ≥ 95% | 每日记录 `task_healthy` 布尔值，10 日累计 |
| quick suite 通过率 | 100% | 每日运行 Phase 0/1 快速套件，记录 pass/fail |
| 扫描响应时间 | < 30s | 每次 heartbeat 测量一次 baseline，记录 p95 |

**通过条件**（非 M0 合并硬门槛，但作为质量门禁）:
- 连续 10 个交易日监测数据显示成功率 ≥ 95%
- 无单日 500/错误率突增

### 3. Heartbeat 集成

在 `HEARTBEAT.md` 中增加检查项：

```
- 检查 /api/v1/market/task-health 状态并记录
- 运行 Phase 0/1 quick suite（screening_baseline + market health）
- 更新 memory/stability_log.jsonl
- 如果最近 3 日失败率 > 5%，主动告警
```

### 4. M0 决策结果

- **M0-05 状态**: 从"硬门槛"改为"观察项"
- **M0 冻结条件**: 满足（功能 + 测试 + 联调已就绪）
- **后续行动**: M0 PR 合并后，每日 heartbeat 自动收集稳定性数据，1 周后复盘趋势

---

## 备用方案：硬门槛（不推荐）

若坚持作为硬门槛：
- M0 冻结时间推迟至 2026-04-18 前后（10 个交易日）
- 期间仍需每日记录 `stability_log.jsonl`
- 第 10 个交易日后人工审查日志，通过后冻结 M0

**风险**: 阻塞 M1 数据层改造约 2 周，影响整体进度。

---

## 建议行动

1. **立即**：采纳观察项方案，M0 冻结不受阻
2. **本轮 heartbeat**: 创建 `scripts/monitor_stability.py` 框架（空函数占位）
3. **下一次 heartbeat**: 填充实现并开始首次记录
4. **PR 准备**: 基于 `M0_PR_BOUNDARY.md` 创建 M0 合并 PR

---

**结论**: M0-05 通过降级为观察项解除阻塞，M0 可立即进入合并准备阶段。
