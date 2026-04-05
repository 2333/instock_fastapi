#!/usr/bin/env python3
"""
M1 执行进度跟踪器

实时监控 M1 任务执行状态，自动更新进度文档，生成执行报告。

用法:
    python scripts/track_m1_progress.py [--watch] [--interval 60]

选项:
    --watch     持续监控模式（默认单次运行）
    --interval  监控间隔（秒，默认 60）
"""

import asyncio
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import argparse
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# 任务定义映射（任务文件 -> 元数据）
TASK_META = {
    # WS-0 基础设施 (5)
    "WS0-01": {"name": "Alembic 基线", "owner": "Agent A", "stream": "WS-0"},
    "WS0-02": {"name": "时间列规范", "owner": "Agent A", "stream": "WS-0"},
    "WS0-03": {"name": "Timescale 规范", "owner": "Agent A", "stream": "WS-0"},
    "WS0-04": {"name": "pro_bar 抽象", "owner": "Agent B", "stream": "WS-0"},
    "WS0-05": {"name": "质量框架骨架", "owner": "Agent F", "stream": "WS-0"},

    # WS-1 核心改造 (5 已准备 + 7 待拆解)
    "WS1-01": {"name": "股票同步", "owner": "Agent C", "stream": "WS-1"},
    "WS1-02": {"name": "日线回填", "owner": "Agent C", "stream": "WS-1"},
    "WS1-03": {"name": "指标引擎", "owner": "Agent D", "stream": "WS-1"},
    "WS1-04": {"name": "分钟线", "owner": "Agent C", "stream": "WS-1"},
    "WS1-05": {"name": "基本面数据", "owner": "Agent C", "stream": "WS-1"},
    # WS1-06~12 待拆解（预留）
    "WS1-06": {"name": "待拆解", "owner": "-", "stream": "WS-1"},
    "WS1-07": {"name": "待拆解", "owner": "-", "stream": "WS-1"},
    "WS1-08": {"name": "待拆解", "owner": "-", "stream": "WS-1"},
    "WS1-09": {"name": "待拆解", "owner": "-", "stream": "WS-1"},
    "WS1-10": {"name": "待拆解", "owner": "-", "stream": "WS-1"},
    "WS1-11": {"name": "待拆解", "owner": "-", "stream": "WS-1"},
    "WS1-12": {"name": "待拆解", "owner": "-", "stream": "WS-1"},

    # WS-2 新接口扩展 (6)
    "WS2-01": {"name": "资金流向", "owner": "Agent E", "stream": "WS-2"},
    "WS2-02": {"name": "涨跌停列表", "owner": "Agent E", "stream": "WS-2"},
    "WS2-03": {"name": "涨跌停明细", "owner": "Agent E", "stream": "WS-2"},
    "WS2-04": {"name": "公告数据", "owner": "Agent E", "stream": "WS-2"},
    "WS2-05": {"name": "历史快照", "owner": "Agent E", "stream": "WS-2"},
    "WS2-06": {"name": "龙虎榜", "owner": "Agent E", "stream": "WS-2"},

    # WS-3 质量保障 (6)
    "WS3-01": {"name": "完整性检查", "owner": "Agent F", "stream": "WS-3"},
    "WS3-02": {"name": "告警配置", "owner": "Agent F", "stream": "WS-3"},
    "WS3-03": {"name": "监测增强", "owner": "Agent F", "stream": "WS-3"},
    "WS3-04": {"name": "数据血缘", "owner": "Agent F", "stream": "WS-3"},
    "WS3-05": {"name": "监控仪表板", "owner": "Agent F", "stream": "WS-3"},
    "WS3-06": {"name": "报告自动化", "owner": "Agent F", "stream": "WS-3"},
}

class M1ProgressTracker:
    """M1 进度跟踪器"""

    def __init__(self):
        self.tracker_path = REPO_ROOT / "docs" / "M1_PROGRESS_TRACKER.md"
        self.execution_log = REPO_ROOT / "logs" / "m1_execution" / "execution.log"
        self.execution_log.parent.mkdir(parents=True, exist_ok=True)
        self.status = {}  # task_id -> status dict

    def load_current_status(self):
        """从跟踪文档解析当前状态"""
        if not self.tracker_path.exists():
            self._initialize_tracker()
            return {}

        content = self.tracker_path.read_text()
        status = {}

        # 解析 Markdown 表格
        # 简化版：查找每行任务状态
        for line in content.split('\n'):
            if '|' in line and 'WS' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4 and parts[1].startswith('WS'):
                    task_id = parts[1]
                    state = parts[3] if len(parts) > 3 else 'pending'
                    status[task_id] = {'state': state, 'raw': line}

        return status

    def _initialize_tracker(self):
        """初始化跟踪文档"""
        template = """# M1 进度跟踪（实时更新）

## 启动时间
{start_time}

## WS-0 基础设施层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
{ws0_rows}

## WS-1 核心改造层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
{ws1_rows}

## WS-2 新接口扩展层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
{ws2_rows}

## WS-3 质量保障层
| Task | 负责人 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|--------|------|---------|---------|------|
{ws3_rows}

## 总体状态
- M1 启动时间: {start_time}
- 当前阶段: 未开始
- 总任务数: 29
- 已完成: 0
- 进行中: 0
- 待开始: 29
- 上次更新: {last_update}

## 执行日志
查看: logs/m1_execution/execution.log
"""
        ws0_rows = "\n".join([f"| {tid} | {TASK_META[tid]['owner']} | pending | - | - | - |" for tid in [f"WS0-0{i}" for i in range(1,6)]])
        ws1_rows = "\n".join([f"| {tid} | {TASK_META[tid]['owner']} | pending | - | - | - |" for tid in [f"WS1-0{i}" for i in range(1,6)] + ["WS1-06", "WS1-07", "WS1-08", "WS1-09", "WS1-10", "WS1-11", "WS1-12"]])
        ws2_rows = "\n".join([f"| {tid} | {TASK_META[tid]['owner']} | pending | - | - | - |" for tid in [f"WS2-0{i}" for i in range(1,6)] + ["WS2-06"]])
        ws3_rows = "\n".join([f"| {tid} | {TASK_META[tid]['owner']} | pending | - | - | - |" for tid in [f"WS3-0{i}" for i in range(1,7)]])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = template.format(
            start_time=now,
            ws0_rows=ws0_rows,
            ws1_rows=ws1_rows,
            ws2_rows=ws2_rows,
            ws3_rows=ws3_rows,
            last_update=now
        )
        self.tracker_path.write_text(content)

    def update_task_status(self, task_id: str, state: str, start_time=None, finish_time=None, note=""):
        """更新单个任务状态"""
        if task_id not in TASK_META:
            print(f"警告: 未知任务 ID {task_id}")
            return

        now = datetime.now().strftime("%H:%M")
        content = self.tracker_path.read_text()

        # 构建新行
        owner = TASK_META[task_id]['owner']
        start = start_time or now
        finish = finish_time or "-"
        note_field = note or "-"

        new_row = f"| {task_id} | {owner} | {state} | {start} | {finish} | {note_field} |"

        # 替换匹配行
        pattern = f"^\\| {re.escape(task_id)} .*"
        lines = content.split('\n')
        updated = False

        for i, line in enumerate(lines):
            if re.match(pattern, line):
                lines[i] = new_row
                updated = True
                break

        if not updated:
            # 未找到，追加到对应区域
            # 简化处理：直接追加到文件末尾（实际应插入对应表格）
            lines.append(new_row)

        # 更新总体统计
        self._update_summary(lines)

        self.tracker_path.write_text('\n'.join(lines))

        # 记录执行日志
        self._log_execution(task_id, state, start_time, finish_time, note)

    def _update_summary(self, lines: list):
        """更新总体状态摘要"""
        # 统计各状态数量
        completed = 0
        in_progress = 0
        pending = 0

        for line in lines:
            if '|' in line and 'WS' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    state = parts[3]
                    if state == 'done':
                        completed += 1
                    elif state == 'in_progress':
                        in_progress += 1
                    elif state == 'pending':
                        pending += 1

        total = completed + in_progress + pending

        # 更新"总体状态"部分
        for i, line in enumerate(lines):
            if line.startswith('- 总任务数:'):
                lines[i] = f"- 总任务数: {total}"
            elif line.startswith('- 已完成:'):
                lines[i] = f"- 已完成: {completed}"
            elif line.startswith('- 进行中:'):
                lines[i] = f"- 进行中: {in_progress}"
            elif line.startswith('- 待开始:'):
                lines[i] = f"- 待开始: {pending}"
            elif line.startswith('- 上次更新:'):
                lines[i] = f"- 上次更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    def _log_execution(self, task_id: str, state: str, start_time, finish_time, note: str):
        """记录执行日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "task_name": TASK_META.get(task_id, {}).get('name', 'unknown'),
            "owner": TASK_META.get(task_id, {}).get('owner', 'unknown'),
            "state": state,
            "start_time": start_time,
            "finish_time": finish_time,
            "note": note
        }
        log_file = self.execution_log
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def _normalize_state(self, state: str) -> str:
        """标准化状态字符串（处理 emoji 前缀和标记格式）"""
        state = state.strip()
        # 移除 emoji
        state_clean = re.sub(r'[⏳✅🔄⚠️❌]', '', state).strip()
        # 处理反引号包裹的状态
        state_clean = re.sub(r'`', '', state_clean).strip().lower()

        if 'done' in state_clean or '完成' in state or '✅' in state:
            return 'completed'
        elif 'progress' in state_clean or 'in_progress' in state_clean or '进行' in state or '🔄' in state:
            return 'in_progress'
        elif 'blocked' in state_clean or '阻塞' in state or '❌' in state:
            return 'blocked'
        else:
            return 'pending'  # todo / 未启动 / ⏳

    def generate_summary_report(self) -> dict:
        """生成进度摘要报告"""
        content = self.tracker_path.read_text()

        # 解析统计
        stats = {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "by_stream": {},
            "last_update": None
        }

        for line in content.split('\n'):
            if '|' in line and 'WS' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    # parts[1] 格式: "WS0-01 Alembic 基线" 或 "WS-0 基础设施"
                    task_field = parts[1]
                    # 提取纯任务 ID (WSx-xx 格式)
                    task_id_match = re.search(r'(WS\d+-\d+)', task_field)
                    if not task_id_match:
                        continue  # 跳过标题行（如 "WS-0 基础设施"）
                    task_id = task_id_match.group(1)
                    raw_state = parts[3]
                    state = self._normalize_state(raw_state)
                    stream = TASK_META.get(task_id, {}).get('stream', 'unknown')

                    stats['total'] += 1
                    stats[state] = stats.get(state, 0) + 1

                    if stream not in stats['by_stream']:
                        stats['by_stream'][stream] = {'total': 0, 'completed': 0, 'in_progress': 0, 'pending': 0}
                    stats['by_stream'][stream]['total'] += 1
                    stats['by_stream'][stream][state] += 1

            elif line.startswith('- 上次更新:'):
                stats['last_update'] = line.split(':', 1)[1].strip()

        return stats

    def print_summary(self):
        """打印进度摘要"""
        stats = self.generate_summary_report()

        print("\n" + "="*50)
        print("M1 进度摘要")
        print("="*50)
        print(f"总任务数: {stats['total']}")
        print(f"已完成:   {stats.get('completed', 0)}")
        print(f"进行中:   {stats.get('in_progress', 0)}")
        print(f"待开始:   {stats.get('pending', 0)}")
        print(f"上次更新: {stats['last_update']}")
        print("\n按工作流:")
        for stream, sstats in stats['by_stream'].items():
            print(f"  {stream}: {sstats['completed']}/{sstats['total']} 完成")
        print("="*50 + "\n")


def main():
    parser = argparse.ArgumentParser(description="M1 进度跟踪器")
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔（秒）")
    args = parser.parse_args()

    tracker = M1ProgressTracker()

    if args.watch:
        print(f"M1 进度监控已启动（间隔 {args.interval}s），按 Ctrl+C 停止")
        try:
            while True:
                tracker.print_summary()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n监控已停止")
    else:
        tracker.print_summary()
        print("提示: 使用 --watch 参数可持续监控进度")


if __name__ == "__main__":
    main()
