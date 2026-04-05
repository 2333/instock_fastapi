#!/usr/bin/env python3
"""
M1 任务状态更新工具

Agent 完成一项任务后，调用此脚本更新进度跟踪。

用法:
    python scripts/update_m1_task.py <task_id> <state> [--start-time HH:MM] [--note "备注"]

参数:
    task_id      任务 ID，如 WS0-01
    state        状态: in_progress | done | failed | pending
    --start-time 开始时间（默认当前时间）
    --note       备注信息

示例:
    # 标记 WS0-01 开始执行
    python scripts/update_m1_task.py WS0-01 in_progress --note "Alembic 初始化中"

    # 标记 WS0-01 完成
    python scripts/update_m1_task.py WS0-01 done --note "基线迁移成功，100+ 表已记录"
"""

import asyncio
import sys
import argparse
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.track_m1_progress import M1ProgressTracker

def main():
    parser = argparse.ArgumentParser(description="更新 M1 任务状态")
    parser.add_argument("task_id", help="任务 ID，如 WS0-01")
    parser.add_argument("state", choices=["pending", "in_progress", "done", "failed"], help="任务状态")
    parser.add_argument("--start-time", help="开始时间（HH:MM，默认当前）")
    parser.add_argument("--note", help="备注信息")
    args = parser.parse_args()

    tracker = M1ProgressTracker()

    # 更新状态
    tracker.update_task_status(
        task_id=args.task_id,
        state=args.state,
        start_time=args.start_time,
        note=args.note or ""
    )

    print(f"✅ 任务 {args.task_id} 状态已更新为 {args.state}")

    # 显示当前摘要
    tracker.print_summary()

    # 记录到执行日志
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "status_update",
        "task_id": args.task_id,
        "new_state": args.state,
        "note": args.note
    }
    log_file = REPO_ROOT / "logs" / "m1_execution" / "state_changes.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a') as f:
        import json
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    main()
