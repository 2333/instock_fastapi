# Task: WS1-04 分钟线数据接入 (minute bars)

**Owner**: Agent C (Data Operations)
**Workstream**: WS-1 核心改造
**Priority**: P1 (高频数据支持)
**Estimated Effort**: 1 天
**Dependencies**: WS0-01, WS0-02, WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `stk_mins` 接口接入，创建分钟线事实表，支持 1/5/15/30/60 分钟周期，建立增量同步机制。

---

## 背景

分钟线数据用于:
- 高频策略回测
- 盘口分析
- 日内交易信号

Tushare 提供 `stk_mins` 接口:
- 频率: 1/5/15/30/60 分钟
- 范围: 股票/指数/基金
- 历史数据量巨大（需谨慎规划存储）

---

## 涉及表

| 表名 | 说明 |
|------|------|
| minute_bars | 分钟线行情事实表（TimescaleDB hypertable） |

---

## 字段映射

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 标的代码 |
| trade_time | trade_time | DateTime | 交易时间（精确到分钟） |
| open | open | Float | 开盘价 |
| high | high | Float | 最高价 |
| low | low | Float | 最低价 |
| close | close | Float | 收盘价 |
| vol | vol | Integer | 成交量（手） |
| amount | amount | Float | 成交额（元） |
| freq | freq | String(3) | 频率: 1min/5min/15min/30min/60min |

**注**: 分钟线使用 `trade_time` (DateTime) 作为时间列，而非 `trade_date`。

---

## 具体步骤

### 1. Model 定义 (`app/models/minute_bar_model.py`)

```python
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

class MinuteBar(Base):
    __tablename__ = "minute_bars"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), ForeignKey('stocks.ts_code'), nullable=False)
    trade_time = Column(DateTime, nullable=False)  # 精确到分钟的时间戳
    freq = Column(String(3), nullable=False)  # 频率标识
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    vol = Column(Integer)  # 成交量（手）
    amount = Column(Float)  # 成交额（元）

    # 关系
    stock = relationship("Stock", back_populates="minute_bars")

    # 约束
    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_time', 'freq', name='uq_minute_bars_ts_code_time_freq'),
        Index('ix_minute_bars_ts_code', 'ts_code'),
        Index('ix_minute_bars_trade_time', 'trade_time'),
        Index('ix_minute_bars_freq', 'freq'),
        Index('ix_minute_bars_ts_code_time', 'ts_code', 'trade_time'),
    )
```

### 2. Alembic 迁移

```bash
alembic revision -m "create-minute-bars-table"
```

迁移脚本:

```python
def upgrade():
    op.create_table(
        'minute_bars',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ts_code', sa.String(12), nullable=False),
        sa.Column('trade_time', sa.DateTime(), nullable=False),
        sa.Column('freq', sa.String(3), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('vol', sa.Integer()),
        sa.Column('amount', sa.Float()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # 唯一约束
    op.create_unique_constraint('uq_minute_bars_ts_code_time_freq', 'minute_bars', ['ts_code', 'trade_time', 'freq'])

    # 索引
    op.create_index('ix_minute_bars_ts_code', 'minute_bars', ['ts_code'])
    op.create_index('ix_minute_bars_trade_time', 'minute_bars', ['trade_time'])
    op.create_index('ix_minute_bars_freq', 'minute_bars', ['freq'])
    op.create_index('ix_minute_bars_ts_code_time', 'minute_bars', ['ts_code', 'trade_time'])

    # 转换为 TimescaleDB hypertable（由 WS0-03 负责或在此执行）
    # op.execute("SELECT create_hypertable('minute_bars', 'trade_time', chunk_time_interval => INTERVAL '1 day')")

def downgrade():
    op.drop_table('minute_bars')
```

### 3. Provider 扩展 (`app/core/crawling/tushare_provider.py`)

```python
class TushareProvider:
    async def fetch_minute_bars(
        self,
        ts_code: str,
        freq: str = "1min",  # 1/5/15/30/60
        start_time: str = "",  # HH:MM
        end_time: str = "",    # HH:MM
        date: str = ""         # 交易日期 YYYYMMDD（为空表示最新）
    ) -> pd.DataFrame:
        """
        获取分钟线数据

        参数:
            ts_code: 股票代码
            freq: 频率 ("1min"/"5min"/"15min"/"30min"/"60min")
            start_time: 开始时间（如 "09:30"）
            end_time: 结束时间（如 "15:00")
            date: 交易日期（如 "20260101"），空表示当天

        返回:
            DataFrame: trade_time/ts_code/open/high/low/close/vol/amount/freq
        """
        pro = ts.pro_api(settings.TUSHARE_TOKEN)

        df = pro.stk_mins(
            ts_code=ts_code,
            freq=freq,
            start_time=start_time,
            end_time=end_time,
            date=date
        )

        if df.empty:
            return df

        # 标准化
        df['trade_time'] = pd.to_datetime(df['trade_time'])
        df['freq'] = freq
        df['ts_code'] = ts_code

        return df[['ts_code', 'trade_time', 'freq', 'open', 'high', 'low', 'close', 'vol', 'amount']]
```

### 4. Repository (`app/repositories/minute_bar_repository.py`)

```python
from sqlalchemy import select, and_
from datetime import datetime, time
from app.models.minute_bar_model import MinuteBar

class MinuteBarRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_date_range(
        self,
        ts_code: str,
        start_date: datetime,
        end_date: datetime,
        freq: str = "1min"
    ) -> list[MinuteBar]:
        """查询日期范围内的分钟线"""
        query = select(MinuteBar).where(
            and_(
                MinuteBar.ts_code == ts_code,
                MinuteBar.trade_time >= start_date,
                MinuteBar.trade_time <= end_date,
                MinuteBar.freq == freq
            )
        ).order_by(MinuteBar.trade_time)
        return await self.session.execute(query).scalars().all()

    async def get_latest(self, ts_code: str, freq: str = "1min") -> MinuteBar:
        """获取最新分钟线记录"""
        query = select(MinuteBar).where(
            and_(
                MinuteBar.ts_code == ts_code,
                MinuteBar.freq == freq
            )
        ).order_by(MinuteBar.trade_time.desc()).limit(1)
        return await self.session.execute(query).scalar_one_or_none()

    async def upsert_many(self, records: list[dict]):
        """批量插入（唯一约束去重）"""
        stmt = insert(MinuteBar).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['ts_code', 'trade_time', 'freq']
        )
        await self.session.execute(stmt)
        await self.session.commit()
```

### 5. 抓取任务 (`app/jobs/tasks/fetch_minute_task.py`)

```python
#!/usr/bin/env python3
"""
分钟线数据同步任务

执行时机:
- 交易日盘中 (9:30-15:00) 每 1/5 分钟触发一次（高频）
- 或盘后批量补全历史

注意: 分钟线数据量巨大，需控制存储成本
"""

import asyncio
from datetime import datetime, time
from app.core.crawling.tushare_provider import TushareProvider
from app.repositories.minute_bar_repository import MinuteBarRepository
from app.repositories.stock_repository import StockRepository

async def fetch_minute_task(date=None, freq="1min"):
    """
    抓取指定日期的分钟线数据

    参数:
        date: 交易日期（None=今日）
        freq: 频率
    """
    provider = TushareProvider()
    repo = MinuteBarRepository()
    stock_repo = StockRepository()

    if date is None:
        date = datetime.now().strftime("%Y%m%d")

    print(f"开始抓取 {date} {freq} 分钟线数据...")

    # 方式 1: 全市场抓取（单次 API）
    df = await provider.fetch_minute_bars(
        ts_code="",  # 空表示全市场
        freq=freq,
        date=date
    )

    if not df.empty:
        records = df.to_dict('records')
        await repo.upsert_many(records)
        print(f"写入 {len(records)} 条分钟线记录")
    else:
        print("无分钟线数据（可能为非交易日或未开盘）")

async def fetch_minute_realtime():
    """盘中实时抓取（每 1 分钟）"""
    while True:
        now = datetime.now()
        if now.time() >= time(9, 30) and now.time() <= time(15, 0):
            await fetch_minute_task(date=now.strftime("%Y%m%d"), freq="1min")
        await asyncio.sleep(60)  # 每分钟执行一次

if __name__ == "__main__":
    asyncio.run(fetch_minute_task())
```

### 6. 数据保留策略（重要）

分钟线数据增长快，需配置 retention:

```sql
-- 在 WS0-03 的 Timescale 策略中增加
SELECT add_retention_policy('minute_bars', INTERVAL '90 days');
-- 保留 90 天，自动删除旧数据
```

或使用连续聚合（Continuous Aggregates）降采样:

```sql
-- 创建 5 分钟降采样视图
CREATE MATERIALIZED VIEW minute_bars_5min
WITH (timescaledb.continuous) AS
SELECT
    ts_code,
    time_bucket('5 minutes', trade_time) AS bucket,
    first(open, trade_time) as open,
    max(high) as high,
    min(low) as low,
    last(close, trade_time) as close,
    sum(vol) as vol,
    sum(amount) as amount
FROM minute_bars
GROUP BY ts_code, bucket;

-- 创建 15 分钟视图
CREATE MATERIALIZED VIEW minute_bars_15min
WITH (timescaledb.continuous) AS
...
```

---

## 验收标准

- [ ] `minute_bars` 表创建成功，hypertable 分区（由 WS0-03 或本任务配置）
- [ ] 唯一约束 `uq_minute_bars_ts_code_time_freq` 生效
- [ ] `fetch_minute_task.py` 可执行，能抓取单日全市场 1 分钟数据
- [ ] 数据量验证: 单日 ~1.5 万条/股票 × 5000 股票 = 7500 万条（需确认实际返回）
- [ ] 幂等性: 重复抓取不产生重复
- [ ] 保留策略/连续聚合配置成功（控制存储成本）
- [ ] 相关测试通过

---

## 交付物

- [ ] `app/models/minute_bar_model.py`
- [ ] Alembic 迁移脚本
- [ ] `app/core/crawling/tushare_provider.py` 扩展 `fetch_minute_bars`
- [ ] `app/repositories/minute_bar_repository.py`
- [ ] `app/jobs/tasks/fetch_minute_task.py`
- [ ] 连续聚合视图（可选）
- [ ] `tests/test_minute_bar_repository.py`

---

## 风险与缓解

| 风险 | 说明 | 缓解 |
|------|------|------|
| 数据量爆炸 | 分钟线日增量 ~7500 万条，年化 200+ 亿 | 配置 retention（90 天）+ 连续聚合降采样 |
| API 频率限制 | Tushare 每分钟最多访问 500 次 | 批量抓取（单次全市场）而非逐股 |
| 存储成本 | 200+ GB/年（估算） | 仅保留热点数据，历史数据存冷存储 |

---

**Trigger**: WS1-03 完成后启动（并行或串行）
**Estimated Time**: 1 天（含 retention 策略配置）
