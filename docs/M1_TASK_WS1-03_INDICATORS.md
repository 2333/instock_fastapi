# Task: WS1-03 技术指标计算引擎

**Owner**: Agent D (Quant & Indicators)
**Workstream**: WS-1 核心改造
**Priority**: P0 (指标数据接入)
**Estimated Effort**: 1 天
**Dependencies**: WS1-02 (日线数据就绪)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现技术指标计算引擎，基于 `daily_bars` 数据计算常用指标（MA/MACD/RSI/Bollinger Bands），并将结果写入 `indicators` 表。

---

## 背景

技术指标是选股与择时的基础。目标:
- 支持主流技术指标计算（至少 10 种）
- 计算性能: 单只股票 10 年数据 < 1 秒
- 支持批量计算（全市场股票）
- 结果标准化存储，便于查询

---

## 涉及表

| 表名 | 说明 |
|------|------|
| indicators | 技术指标结果表 |

---

## 具体步骤

### 1. Model 定义 (`app/models/indicator_model.py`)

```python
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

class Indicator(Base):
    __tablename__ = "indicators"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), ForeignKey('stocks.ts_code'), nullable=False)
    trade_date_dt = Column(DateTime, nullable=False)
    indicator_name = Column(String(30), nullable=False)  # e.g. 'ma_5', 'macd'
    value = Column(Float)  # 单值指标
    values = Column(JSON)  # 多值指标（如 MACD 含 DIF/DEA/MACD）

    # 关系
    stock = relationship("Stock", back_populates="indicators")

    # 联合唯一约束
    __table_args__ = (
        UniqueConstraint('ts_code', 'indicator_name', 'trade_date_dt', name='uq_indicators_ts_code_name_date'),
        Index('ix_indicators_ts_code', 'ts_code'),
        Index('ix_indicators_trade_date_dt', 'trade_date_dt'),
        Index('ix_indicators_name', 'indicator_name'),
    )
```

### 2. 指标计算引擎 (`app/services/indicator_engine.py`)

```python
import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Any
from app.models.indicator_model import Indicator

class IndicatorEngine:
    """技术指标计算引擎"""

    # 支持的指标配置
    INDICATOR_CONFIG = {
        'ma_5': {'func': 'ma', 'params': {'timeperiod': 5}},
        'ma_10': {'func': 'ma', 'params': {'timeperiod': 10}},
        'ma_20': {'func': 'ma', 'params': {'timeperiod': 20}},
        'ma_60': {'func': 'ma', 'params': {'timeperiod': 60}},
        'ema_12': {'func': 'ema', 'params': {'timeperiod': 12}},
        'ema_26': {'func': 'ema', 'params': {'timeperiod': 26}},
        'macd': {'func': 'macd', 'params': {'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9}},
        'rsi_14': {'func': 'rsi', 'params': {'timeperiod': 14}},
        'boll_upper': {'func': 'bbands', 'params': {'timeperiod': 20, 'nbdevup': 2}, 'output': 0},
        'boll_middle': {'func': 'bbands', 'params': {'timeperiod': 20, 'nbdevup': 2}, 'output': 1},
        'boll_lower': {'func': 'bbands', 'params': {'timeperiod': 20, 'nbdevup': 2}, 'output': 2},
        'kdj_k': {'func': 'stoch', 'params': {'fastk_period': 9, 'slowk_period': 3, 'slowd_period': 3}, 'output': 0},
        'kdj_d': {'func': 'stoch', 'params': {'fastk_period': 9, 'slowk_period': 3, 'slowd_period': 3}, 'output': 1},
    }

    def __init__(self):
        self._cache = {}  # 缓存计算结果

    def calculate(self, df: pd.DataFrame, indicator_names: List[str]) -> pd.DataFrame:
        """
        计算技术指标

        参数:
            df: 必须包含列 ['open', 'high', 'low', 'close', 'vol']
            indicator_names: 要计算的指标名称列表

        返回:
            包含指标值的 DataFrame (与原 df index 对齐)
        """
        results = pd.DataFrame(index=df.index)

        for name in indicator_names:
            config = self.INDICATOR_CONFIG.get(name)
            if not config:
                raise ValueError(f"不支持的指标: {name}")

            func_name = config['func']
            params = config['params']
            output_idx = config.get('output', None)

            # 调用 TA-Lib
            func = getattr(talib, func_name.upper())
            args = self._prepare_args(df, func_name, params)

            output = func(*args)

            # 处理多输出
            if output_idx is not None:
                results[name] = output[output_idx]
            elif isinstance(output, (list, tuple)):
                # 多值指标存入 JSON 字段
                results[name] = [list(v) for v in zip(*output)]
            else:
                results[name] = output

        return results

    def _prepare_args(self, df: pd.DataFrame, func_name: str, params: dict):
        """准备 TA-Lib 函数参数"""
        if func_name in ['ma', 'ema', 'rsi', 'adx']:
            return (df['close'].values, params['timeperiod'])
        elif func_name in ['macd']:
            return (df['close'].values, params['fastperiod'], params['slowperiod'], params['signalperiod'])
        elif func_name in ['bbands']:
            return (df['close'].values, params['timeperiod'], params['nbdevup'], params['nbdevdn'])
        elif func_name in ['stoch']:
            return (
                df['high'].values, df['low'].values, df['close'].values,
                params['fastk_period'], params['slowk_period'], params['slowd_period']
            )
        else:
            raise NotImplementedError(f"未实现参数映射: {func_name}")

# 全局单例
indicator_engine = IndicatorEngine()
```

### 3. 批量计算任务 (`app/jobs/tasks/compute_indicators.py`)

```python
#!/usr/bin/env python3
"""
批量计算技术指标任务

支持增量计算（仅计算缺失日期）
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from app.services.indicator_engine import indicator_engine
from app.repositories.daily_bar_repository import DailyBarRepository
from app.repositories.indicator_repository import IndicatorRepository

async def compute_indicators_task(target_date=None):
    """
    计算指定日期或最新日期的技术指标

    参数:
        target_date: 指定日期（格式 YYYY-MM-DD），None 表示最新交易日
    """
    daily_repo = DailyBarRepository()
    indicator_repo = IndicatorRepository()

    # 确定计算目标日期
    if target_date is None:
        target_date = await daily_repo.get_latest_trade_date()
    else:
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    print(f"开始计算 {target_date} 的技术指标...")

    # 获取当日所有股票的日线数据
    daily_data = await daily_repo.get_by_date(target_date)

    print(f"股票数量: {len(daily_data)}")

    # 为每只股票计算指标（需要足够的历史数据）
    indicators_to_compute = ['ma_5', 'ma_10', 'ma_20', 'ma_60', 'macd', 'rsi_14']

    for stock_code, df in daily_data.groupby('ts_code'):
        # 获取该股票足够的历史数据（例如 MA60 需要 60 天）
        history = await daily_repo.get_recent(stock_code, days=60)

        if len(history) < 60:
            print(f"警告: {stock_code} 历史数据不足（{len(history)} 天），跳过")
            continue

        # 计算指标
        result_df = indicator_engine.calculate(history, indicators_to_compute)

        # 提取 target_date 当天的指标值
        today_idx = result_df.index[result_df.index.date == target_date]
        if len(today_idx) == 0:
            continue

        today_values = result_df.loc[today_idx[0]]

        # 转换为 Indicator 记录
        records = []
        for col in today_values.index:
            value = today_values[col]
            if pd.isna(value):
                continue

            record = {
                'ts_code': stock_code,
                'trade_date_dt': target_date,
                'indicator_name': col,
                'value': float(value) if not isinstance(value, dict) else None,
                'values': value if isinstance(value, dict) else None,
            }
            records.append(record)

        # 写入数据库
        await indicator_repo.upsert_many(records)

    print(f"指标计算完成。写入 {len(records)} 条记录（估算）")

if __name__ == "__main__":
    asyncio.run(compute_indicators_task())
```

### 4. 验证脚本 (`scripts/verify_indicators.py`)

```python
#!/usr/bin/env python3
import psycopg2
from datetime import datetime

def verify():
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # 1. 总记录数
    cur.execute("SELECT COUNT(*) FROM indicators")
    print(f"indicators 总记录数: {cur.fetchone()[0]:,}")

    # 2. 指标类型分布
    cur.execute("""
        SELECT indicator_name, COUNT(*) as cnt
        FROM indicators
        GROUP BY indicator_name
        ORDER BY cnt DESC
    """)
    print("\n指标类型分布:")
    for name, cnt in cur.fetchall():
        print(f"  {name}: {cnt:,}")

    # 3. 日期范围
    cur.execute("SELECT MIN(trade_date_dt), MAX(trade_date_dt) FROM indicators")
    min_d, max_d = cur.fetchone()
    print(f"\n指标时间范围: {min_d} ~ {max_d}")

    # 4. 缺失检查（某股票某日应有多少指标）
    cur.execute("""
        SELECT ts_code, trade_date_dt, COUNT(*) as indicator_count
        FROM indicators
        WHERE trade_date_dt = CURRENT_DATE - INTERVAL '1 day'
        GROUP BY ts_code, trade_date_dt
        HAVING COUNT(*) < 10
        LIMIT 10
    """)
    rows = cur.fetchall()
    if rows:
        print(f"\n指标不足的股票（昨日）: {len(rows)} 只")
    else:
        print("\n所有股票指标齐全")

    conn.close()

if __name__ == "__main__":
    verify()
```

---

## 验收标准

- [ ] `indicators` 表结构正确（ts_code/trade_date_dt/indicator_name/value/values）
- [ ] 唯一约束 `uq_indicators_ts_code_name_date` 创建成功
- [ ] `compute_indicators_task.py` 可执行，计算至少 10 种指标
- [ ] 单只股票 10 年数据指标计算时间 < 1 秒
- [ ] 全市场批量计算（5000 只）< 1 小时
- [ ] 增量计算: 重复执行不会重复写入（唯一约束保护）
- [ ] `scripts/verify_indicators.py` 输出符合预期

---

## 交付物

- [ ] `app/models/indicator_model.py`
- [ ] Alembic 迁移（创建 indicators 表 + 约束）
- [ ] `app/services/indicator_engine.py`（计算引擎）
- [ ] `app/jobs/tasks/compute_indicators.py`（批量任务）
- [ ] `scripts/verify_indicators.py`（验证脚本）
- [ ] `tests/test_indicator_engine.py`（指标计算单元测试）

---

**Trigger**: WS1-02 完成后启动
**Estimated Time**: 1 天（含全市场批量计算）
