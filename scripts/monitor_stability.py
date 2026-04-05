#!/usr/bin/env python3
"""
每日稳定性监测脚本（Heartbeat 驱动）

记录内容:
- latest_trade_date: 最新交易日（从数据库或 API 获取）
- task_healthy: /api/v1/market/task-health 返回的健康状态
- quick_suite_passed: Phase 0/1 快速回归套件执行结果
- scan_latency_ms: 全市场扫描基线耗时（快速测量）

输出: memory/stability_log.jsonl（每行一条 JSON 记录）
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# 配置：将仓库根目录加入 sys.path，确保 app 模块可导入
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
LOG_FILE = REPO_ROOT / "memory" / "stability_log.jsonl"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PYTEST = [str(VENV_PYTHON), "-m", "pytest"]


def get_latest_trade_date():
    """从数据库查询最新交易日（如无法连接返回 None）"""
    try:
        import asyncio
        from app.database import async_engine, async_session
        from sqlalchemy import text

        async def _query():
            async with async_session() as s:
                rs = await s.execute(text("SELECT MAX(trade_date) FROM daily_bars"))
                return rs.scalar()

        return asyncio.run(_query())
    except Exception:
        return None


def check_task_health():
    """调用内部函数检查任务健康状态（如不可用返回 None）"""
    try:
        from app.services.scheduler_service import get_task_health_summary
        summary = get_task_health_summary()
        return summary.get("healthy", False)
    except Exception:
        return None


def run_quick_suite():
    """运行 Phase 0/1 快速回归套件"""
    tests = [
        "tests/test_screening_baseline.py",
        "tests/test_api.py::TestMarketTaskHealthAPI",
        "tests/test_selection_market_services.py",
        "tests/test_selection_today_summary.py",
        "tests/test_backtest_report_structure.py",
        "tests/test_strategy_selection_bridge.py",
    ]
    result = subprocess.run(
        PYTEST + tests,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    passed = result.returncode == 0
    # 提取passed数量（简单解析）
    return passed, result.stdout + result.stderr


def measure_scan_latency():
    """快速测量扫描接口响应时间（调用一次 /screening/run）"""
    # 注：完整测量需要启动 app 实例，此处暂时禁用，仅返回 None
    # 后续可改为调用 pytest 中的性能测试或独立 locust 脚本
    return None, "skipped"


def record_entry(entry: dict):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def summarize_last_n_days(n=10):
    """计算最近 n 天通过率（忽略 quick_suite_passed 为 null/None 的记录）"""
    if not LOG_FILE.exists():
        return None
    lines = LOG_FILE.read_text().strip().splitlines()[-n:]
    if not lines:
        return None
    total = 0
    passed = 0
    for ln in lines:
        rec = json.loads(ln)
        val = rec.get("quick_suite_passed")
        if val is None:
            continue  # 跳过无法判定的记录
        total += 1
        if val:
            passed += 1
    return round(passed / total * 100, 1) if total else None


def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] Stability check starting...")

    # 1. 交易日
    trade_date = get_latest_trade_date()
    print(f"  Latest trade date: {trade_date}")

    # 2. 任务健康
    healthy = check_task_health()
    print(f"  Task healthy: {healthy}")

    # 3. quick suite
    suite_ok, suite_out = run_quick_suite()
    print(f"  Quick suite: {'PASS' if suite_ok else 'FAIL'}")

    # 4. 扫描耗时（可选，仅测量一次）
    latency_ms, status = measure_scan_latency()
    print(f"  Scan latency: {latency_ms}ms (status={status})")

    # 5. 记录
    entry = {
        "timestamp": timestamp,
        "trading_day": str(trade_date) if trade_date else None,
        "task_healthy": healthy,
        "quick_suite_passed": suite_ok,
        "scan_latency_ms": latency_ms,
        "scan_status": status,
    }
    record_entry(entry)
    print(f"  Recorded to {LOG_FILE}")

    # 6. 汇总
    rate_10d = summarize_last_n_days(10)
    if rate_10d is not None:
        print(f"  Last 10-day stability rate: {rate_10d}%")
        if rate_10d < 95:
            print("  ⚠️  WARNING: Stability below 95% threshold")
    else:
        print("  (accumulating data, need 10 days)")

    return 0 if suite_ok else 1


if __name__ == "__main__":
    sys.exit(main())
