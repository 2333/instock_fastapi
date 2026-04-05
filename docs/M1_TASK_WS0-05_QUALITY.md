# Task: WS0-05 数据质量框架骨架

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-0 基础设施
**Priority**: P0 (支撑 WS-3 质量保障)
**Estimated Effort**: 0.5 天
**Dependencies**: 无
**Status**: Ready to assign (等待 M1 启动信号)

---

## 任务描述

建立数据质量检查框架，为 WS-3 后续填充检查项（完整性、范围、跨源一致性）提供扩展点。当前阶段仅搭建骨架，检查项为占位（始终 PASS）。

---

## 背景

数据质量保障是 M1 验收的关键:
- **完整性**: 每日数据行数 vs Tushare 基准
- **范围校验**: 日期范围、代码覆盖度
- **跨源一致性**: Tushare vs EastMoney 关键字段对比
- **告警**: 失败/缺失率超过阈值时通知

本任务不实现具体检查逻辑，只定义框架与 CLI 入口。

---

## 具体步骤

### 1. 创建 `app/services/data_quality.py`

```python
"""
数据质量检查框架

设计原则:
- 每个检查项实现 CheckResult 协议
- 检查器可注册、可配置
- 支持批量执行与报告生成
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class CheckResult:
    """单次检查结果"""
    check_name: str
    passed: bool
    details: Dict[str, Any]
    suggestions: List[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self):
        return asdict(self)

class DataQualityCheck(ABC):
    """质量检查抽象基类"""

    @abstractmethod
    def name(self) -> str:
        """检查项名称"""
        pass

    @abstractmethod
    def description(self) -> str:
        """检查描述"""
        pass

    @abstractmethod
    async def run(self) -> CheckResult:
        """执行检查，返回结果"""
        pass

class QualityEngine:
    """质量检查引擎"""

    def __init__(self):
        self._checks: List[DataQualityCheck] = []

    def register(self, check: DataQualityCheck):
        """注册检查项"""
        self._checks.append(check)

    async def run_all(self) -> List[CheckResult]:
        """运行所有检查"""
        results = []
        for check in self._checks:
            try:
                result = await check.run()
                results.append(result)
            except Exception as e:
                results.append(CheckResult(
                    check_name=check.name(),
                    passed=False,
                    details={"error": str(e)},
                    suggestions=["检查实现有异常，请联系开发团队"]
                ))
        return results

    def summary(self, results: List[CheckResult]) -> Dict[str, Any]:
        """生成汇总报告"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
            "timestamp": datetime.now().isoformat(),
        }

# 全局引擎实例
quality_engine = QualityEngine()
```

### 2. 实现占位检查项（始终 PASS）

在 `app/services/data_quality.py` 追加:

```python
class CompletenessCheck(DataQualityCheck):
    """完整性检查（占位）"""

    def name(self) -> str:
        return "completeness"

    def description(self) -> str:
        return "检查数据表完整性（行数 vs 基准）"

    async def run(self) -> CheckResult:
        # TODO: WS-3 实现实际逻辑
        return CheckResult(
            check_name=self.name(),
            passed=True,
            details={"note": "占位检查，实际逻辑待 WS-3 实现"},
            suggestions=["无"]
        )

class RangeCheck(DataQualityCheck):
    """范围校验（占位）"""
    def name(self) -> str:
        return "range"

    def description(self) -> str:
        return "校验日期范围与代码覆盖"

    async def run(self) -> CheckResult:
        return CheckResult(
            check_name=self.name(),
            passed=True,
            details={"note": "占位检查，实际逻辑待 WS-3 实现"},
            suggestions=["无"]
        )

class CrossSourceConsistencyCheck(DataQualityCheck):
    """跨源一致性（占位）"""
    def name(self) -> str:
        return "cross_source"

    def description(self) -> str:
        return "Tushare vs EastMoney 关键字段对比"

    async def run(self) -> CheckResult:
        return CheckResult(
            check_name=self.name(),
            passed=True,
            details={"note": "占位检查，实际逻辑待 WS-3 实现"},
            suggestions=["无"]
        )

# 注册默认检查项
quality_engine.register(CompletenessCheck())
quality_engine.register(RangeCheck())
quality_engine.register(CrossSourceConsistencyCheck())
```

### 3. 创建 CLI 入口 `scripts/run_quality_checks.py`

```python
#!/usr/bin/env python3
"""
数据质量检查 CLI

用法:
    python scripts/run_quality_checks.py [--json] [--fail-on-error]

选项:
    --json        输出 JSON 格式报告
    --fail-on-error  任何检查失败则 exit code 1
"""

import asyncio
import sys
import json
from pathlib import Path
import argparse

# 添加项目根目录到路径
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.services.data_quality import quality_engine

async def main():
    parser = argparse.ArgumentParser(description="Run data quality checks")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit 1 if any check fails")
    args = parser.parse_args()

    print("=== 数据质量检查 ===\n")

    # 运行所有检查
    results = await quality_engine.run_all()

    # 打印摘要
    summary = quality_engine.summary(results)
    print(f"总计: {summary['total']} 项检查")
    print(f"通过: {summary['passed']} 项")
    print(f"失败: {summary['failed']} 项")
    print(f"通过率: {summary['pass_rate']}%")

    # 打印详细结果
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"\n{status} {r.check_name}: {r.details}")

    # JSON 输出
    if args.json:
        output = {
            "summary": summary,
            "results": [r.to_dict() for r in results],
        }
        print("\n--- JSON OUTPUT ---")
        print(json.dumps(output, ensure_ascii=False, indent=2))

    # 退出码
    if args.fail_on_error and summary['failed'] > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. 基础测试 `tests/test_data_quality.py`

```python
import pytest
from app.services.data_quality import quality_engine, CheckResult

@pytest.mark.asyncio
async def test_quality_engine_runs():
    results = await quality_engine.run_all()
    assert len(results) > 0
    for r in results:
        assert isinstance(r, CheckResult)
        assert r.check_name
        assert r.passed is not None  # 当前占位检查应全部通过
```

---

## 验收标准

- [ ] `QualityEngine` 可实例化并注册检查项
- [ ] `run_all()` 返回 `List[CheckResult]`
- [ ] 占位检查项（completeness/range/cross_source）全部通过
- [ ] `scripts/run_quality_checks.py` 可执行，输出人类可读报告 + JSON 格式
- [ ] `tests/test_data_quality.py` 通过

---

## 交付物

- [ ] `app/services/data_quality.py`（框架 + 3 个占位检查）
- [ ] `scripts/run_quality_checks.py`（CLI 入口）
- [ ] `tests/test_data_quality.py`（基础测试）
- [ ] `docs/DATA_QUALITY_FRAMEWORK.md`（可选，框架说明）

---

## 后续（WS-3 填充）

WS-3 任务将:
1. 替换占位检查为实际逻辑
2. 增加更多检查项（时序健康、告警规则）
3. 集成到 heartbeat 与监控系统

---

**Trigger**: M1 启动信号
**Estimated Time**: 0.5 天（框架）+ WS-3 后续填充
