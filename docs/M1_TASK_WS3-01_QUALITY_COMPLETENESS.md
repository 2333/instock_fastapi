# Task: WS3-01 数据质量检查实现（completeness）

**Owner**: Agent F (Quality & Observability)
**Workstream**: WS-3 质量保障
**Priority**: P0 (质量体系核心)
**Estimated Effort**: 0.5 天
**Dependencies**: WS0-05 (质量框架骨架)、WS1-02 (日线数据就绪)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 `CompletenessCheck` 的具体逻辑，验证每日数据完整性（行数 vs Tushare 基准），确保数据覆盖率达标。

---

## 背景

数据完整性是质量第一关:
- 每日应覆盖所有上市股票（除停牌）
- 历史交易日数应匹配（~250 天/年）
- 缺失率需低于阈值（如 1%）

`WS0-05` 已搭建框架，本任务填充实际检查逻辑。

---

## 具体步骤

### 1. 更新 `app/services/data_quality.py`

```python
class CompletenessCheck(DataQualityCheck):
    """完整性检查（实现）"""

    def name(self) -> str:
        return "completeness.daily_bars"

    def description(self) -> str:
        return "检查 daily_bars 表数据完整性（行数 vs 基准）"

    async def run(self) -> CheckResult:
        from app.repositories.daily_bar_repository import DailyBarRepository
        from app.repositories.stock_repository import StockRepository
        from datetime import datetime, timedelta

        daily_repo = DailyBarRepository()
        stock_repo = StockRepository()

        # 获取昨日日期（交易日）
        yesterday = (datetime.now() - timedelta(days=1)).date()

        # 1. 获取昨日日线数据行数
        daily_count = await daily_repo.count_by_date(yesterday)

        # 2. 获取昨日应上市股票数（排除停牌）
        active_stocks = await stock_repo.get_all_active()
        expected_count = len(active_stocks)

        # 3. 计算覆盖率
        coverage = daily_count / expected_count if expected_count > 0 else 0

        # 4. 判断是否通过阈值（如 99%）
        threshold = 0.99
        passed = coverage >= threshold

        details = {
            "date": yesterday.isoformat(),
            "actual_count": daily_count,
            "expected_count": expected_count,
            "coverage_rate": round(coverage * 100, 2),
            "threshold": round(threshold * 100, 2)
        }

        suggestions = []
        if not passed:
            suggestions.append(f"覆盖率低于阈值 {threshold*100}%，请检查数据抓取是否完整")
            suggestions.append("查看 fetch_daily_task 日志确认无错误")
            suggestions.append("检查 Tushare 接口是否返回全量数据")

        return CheckResult(
            check_name=self.name(),
            passed=passed,
            details=details,
            suggestions=suggestions
        )
```

### 2. Repository 方法扩展

`app/repositories/daily_bar_repository.py`:

```python
async def count_by_date(self, trade_date: date) -> int:
    """统计指定日期的数据行数"""
    from sqlalchemy import func
    query = select(func.count(DailyBar.id)).where(DailyBar.trade_date_dt == trade_date)
    result = await self.session.execute(query)
    return result.scalar_one()
```

### 3. 测试 `tests/test_data_quality_completeness.py`

```python
import pytest
from app.services.data_quality import quality_engine
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_completeness_check():
    # Mock repository 返回
    with patch('app.services.data_quality.DailyBarRepository') as MockDailyRepo, \
         patch('app.services.data_quality.StockRepository') as MockStockRepo:

        mock_daily = MockDailyRepo.return_value
        mock_daily.count_by_date = AsyncMock(return_value=4950)

        mock_stock = MockStockRepo.return_value
        mock_stock.get_all_active = AsyncMock(return_value=[1]*5000)  # 5000 只股票

        results = await quality_engine.run_all()
        completeness_result = next(r for r in results if r.check_name == "completeness.daily_bars")

        assert completeness_result.passed is True
        assert completeness_result.details["coverage_rate"] == 99.0
```

### 4. 集成到 `scripts/run_quality_checks.py`

确保引擎注册了新的实现（已在 WS0-05 注册）。

---

## 验收标准

- [ ] `CompletenessCheck.run()` 返回正确的覆盖率计算
- [ ] 覆盖率 ≥ 99% 时通过，< 99% 时失败
- [ ] 测试通过（含 mock 场景）
- [ ] `scripts/run_quality_checks.py` 输出包含此项检查

---

## 交付物

- [ ] `app/services/data_quality.py` 更新（CompletenessCheck 实现）
- [ ] `app/repositories/daily_bar_repository.py` 新增 `count_by_date`
- [ ] `tests/test_data_quality_completeness.py`
- [ ] `docs/DATA_QUALITY_CHECKS.md`（更新 completeness 部分）

---

**Trigger**: M1 启动后，WS1-02 日线数据就绪后执行
**Estimated Time**: 0.5 天
