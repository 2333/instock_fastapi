# Task: WS3-03 稳定性监测增强

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-3 质量保障
**Priority**: P1 (运维可用性)
**Estimated Effort**: 0.5 天
**Dependencies**: WS0-05 (稳定性监测骨架)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

增强 `scripts/monitor_stability.py`，增加更多健康检查维度（数据库连接池、磁盘空间、TimescaleDB 状态、任务延迟检测），并提供历史趋势报告。

---

## 背景

当前 `monitor_stability.py` 仅检查 quick suite 通过率，需扩展:
- 基础设施健康: 数据库连接池、磁盘空间、内存
- TimescaleDB 状态: hypertable 数量、chunk 状态
- 任务延迟: fetch_daily_task 是否按时执行
- 历史趋势: 通过率变化、失败模式分析

---

## 具体步骤

### 1. 扩展监控脚本 `scripts/monitor_stability.py`

```python
#!/usr/bin/env python3
"""
稳定性监测增强版

检查项:
1. Quick suite 通过率（已有）
2. 数据库连接池状态
3. 磁盘空间（数据目录）
4. TimescaleDB hypertable 健康
5. 任务执行延迟检测
6. 历史趋势报告
"""

import psutil
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
import json

# 数据目录
DATA_DIR = Path("/var/lib/postgresql/15/main")  # 根据实际调整

def check_db_connections():
    """检查数据库连接池"""
    conn = psycopg2.connect(...)
    cur = conn.cursor()
    cur.execute("""
        SELECT count(*) FROM pg_stat_activity
        WHERE datname = 'instockdb'
    """)
    active = cur.fetchone()[0]
    cur.execute("SHOW max_connections")
    max_conn = cur.fetchone()[0]
    utilization = active / max_conn
    return {
        "active_connections": active,
        "max_connections": max_conn,
        "utilization": round(utilization * 100, 2),
        "status": "ok" if utilization < 0.8 else "warning"
    }

def check_disk_space():
    """检查磁盘空间"""
    usage = psutil.disk_usage(DATA_DIR)
    return {
        "total_gb": round(usage.total / 1e9, 2),
        "used_gb": round(usage.used / 1e9, 2),
        "free_gb": round(usage.free / 1e9, 2),
        "percent_used": usage.percent,
        "status": "ok" if usage.percent < 85 else "warning" if usage.percent < 95 else "critical"
    }

def check_timescale_health():
    """检查 TimescaleDB 状态"""
    conn = psycopg2.connect(...)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM timescaledb_information.hypertables
    """)
    hypertable_count = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM timescaledb_information.chunks
        WHERE status = 'pending'  -- 未压缩的 chunk
    """)
    uncompressed_chunks = cur.fetchone()[0]
    return {
        "hypertable_count": hypertable_count,
        "uncompressed_chunks": uncompressed_chunks,
        "status": "ok" if uncompressed_chunks < 100 else "warning"
    }

def check_task_latency():
    """检查任务执行延迟（通过日志）"""
    log_file = Path("logs/fetch_daily.log")
    if not log_file.exists():
        return {"status": "unknown", "message": "日志文件不存在"}

    # 读取最后 N 行
    with open(log_file) as f:
        lines = f.readlines()[-100:]

    # 解析执行时间
    last_run = None
    for line in reversed(lines):
        if "开始抓取" in line:
            # 解析时间戳
            ts_str = line[:19]  # 假设格式 "2026-04-05 15:30:00"
            last_run = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            break

    if last_run is None:
        return {"status": "warning", "message": "未找到任务执行记录"}

    now = datetime.now()
    # 判断是否延迟（应在 15:30 执行）
    expected_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now < expected_time:
        return {"status": "ok", "message": "任务尚未到执行时间"}

    delay = now - last_run
    # 如果任务在 15:30 后 1 小时内未执行，告警
    status = "ok" if delay < timedelta(hours=1) else "warning"
    return {
        "last_run": last_run.isoformat(),
        "delay_minutes": delay.total_seconds() / 60,
        "status": status
    }

def generate_trend_report():
    """生成历史趋势报告（基于 stability_log.jsonl）"""
    log_path = Path("memory/stability_log.jsonl")
    if not log_path.exists():
        return {}

    # 读取最近 7 天记录
    records = []
    with open(log_path) as f:
        for line in f:
            rec = json.loads(line)
            rec_time = datetime.fromisoformat(rec["timestamp"])
            if (datetime.now() - rec_time).days <= 7:
                records.append(rec)

    # 统计通过率趋势
    dates = {}
    for rec in records:
        date = rec["timestamp"][:10]
        if date not in dates:
            dates[date] = {"total": 0, "passed": 0}
        dates[date]["total"] += 1
        if rec.get("quick_suite") == "PASS":
            dates[date]["passed"] += 1

    trend = {}
    for date, stats in sorted(dates.items()):
        trend[date] = {
            "pass_rate": round(stats["passed"] / stats["total"] * 100, 1) if stats["total"] else 0,
            "checks": stats["total"]
        }

    return trend

def main():
    print("=== 稳定性监测增强版 ===\n")

    results = {
        "timestamp": datetime.now().isoformat(),
        "quick_suite": check_quick_suite(),  # 原有逻辑
        "db_connections": check_db_connections(),
        "disk_space": check_disk_space(),
        "timescale_health": check_timescale_health(),
        "task_latency": check_task_latency(),
        "trend_7d": generate_trend_report(),
    }

    # 打印摘要
    print(f"数据库连接: {results['db_connections']['status']} ({results['db_connections']['utilization']}%)")
    print(f"磁盘空间: {results['disk_space']['status']} ({results['disk_space']['percent_used']}%)")
    print(f"TimescaleDB: {results['timescale_health']['status']} (hypertables={results['timescale_health']['hypertable_count']})")
    print(f"任务延迟: {results['task_latency']['status']}")

    # 记录到日志
    log_path = Path("memory/stability_log.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(results, ensure_ascii=False) + "\n")

    # 判断总体健康度
    overall_status = "PASS"
    for key in ["db_connections", "disk_space", "timescale_health", "task_latency"]:
        if results[key]["status"] != "ok":
            overall_status = "FAIL"

    print(f"\n总体状态: {overall_status}")
    return 0 if overall_status == "PASS" else 1

if __name__ == "__main__":
    exit(main())
```

### 2. 测试

```bash
# 手动运行验证
python scripts/monitor_stability.py
# 应输出各维度检查结果与总体状态
```

### 3. 集成到 Heartbeat

HEARTBEAT 周期调用此脚本即可。

---

## 验收标准

- [ ] `check_db_connections()` 返回连接池利用率
- [ ] `check_disk_space()` 返回磁盘使用率与状态
- [ ] `check_timescale_health()` 返回 hypertable 数量与未压缩 chunk 数
- [ ] `check_task_latency()` 检测 fetch_daily_task 延迟
- [ ] `generate_trend_report()` 生成近 7 天通过率趋势
- [ ] 脚本可执行，日志写入 `memory/stability_log.jsonl`
- [ ] 测试通过

---

## 交付物

- [ ] `scripts/monitor_stability.py` 增强版
- [ ] `tests/test_monitor_stability.py`（各检查函数单元测试）
- [ ] `docs/MONITORING_GUIDE.md`（监控指标说明）

---

**Trigger**: WS3-02 完成后
**Estimated Time**: 0.5 天
