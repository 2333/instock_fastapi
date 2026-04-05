# Task: WS2-01 资金流向表 (moneyflow) 接入

**Owner**: Agent E (Integration Specialist)
**Workstream**: WS-2 新接口扩展
**Priority**: P1 (高价值数据源)
**Estimated Effort**: 0.5 天
**Dependencies**: WS0-01, WS0-02, WS0-03
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `moneyflow` 接口的接入，创建 `moneyflow` 事实表，建立每日增量同步任务。

---

## 背景

资金流向数据是分析主力资金动向的关键指标:
- 包含大单/中单/小单买卖统计
- 可用于识别机构行为
- 每日更新，数据量 ~5000 条/日

目标:
- 创建 `moneyflow` 表（TimescaleDB hypertable）
- 实现 `fetch_moneyflow` 抓取任务
- 每日增量同步（收盘后执行）

---

## 涉及表

| 表名 | 说明 |
|------|------|
| moneyflow | 资金流向事实表 |

---

## 字段映射（Tushare → DB）

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 股票代码 |
| trade_date | trade_date | String(8) | 交易日（YYYYMMDD） |
| buy_sm_vol | buy_sm_vol | Integer | 小单买入量（手） |
| buy_sm_amount | buy_sm_amount | Float | 小单买入额（万元） |
| sell_sm_vol | sell_sm_vol | Integer | 小单卖出量 |
| sell_sm_amount | sell_sm_amount | Float | 小单卖出额 |
| buy_md_vol | buy_md_vol | Integer | 中单买入量 |
| buy_md_amount | buy_md_amount | Float | 中单买入额 |
| sell_md_vol | sell_md_vol | Integer | 中单卖出量 |
| sell_md_amount | sell_md_amount | Float | 中单卖出额 |
| buy_lg_vol | buy_lg_vol | Integer | 大单买入量 |
| buy_lg_amount | buy_lg_amount | Float | 大单买入额 |
| sell_lg_vol | sell_lg_vol | Integer | 大单卖出量 |
| sell_lg_amount | sell_lg_amount | Float | 大单卖出额 |
| buy_elg_vol | buy_elg_vol | Integer | 特大单买入量 |
| buy_elg_amount | buy_elg_amount | Float | 特大单买入额 |
| sell_elg_vol | sell_elg_vol | Integer | 特大单卖出量 |
| sell_elg_amount | sell_elg_amount | Float | 特大单卖出额 |
| net_mf_vol | net_mf_vol | Integer | 净流入量（手） |
| net_mf_amount | net_mf_amount | Float | 净流入额（万元） |

**注**: `trade_date` 需转换为 `trade_date_dt` (DateTime)。

---

## 具体步骤

### 1. Model 定义 (`app/models/moneyflow_model.py`)

```python
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

class MoneyFlow(Base):
    __tablename__ = "moneyflow"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), ForeignKey('stocks.ts_code'), nullable=False)
    trade_date_dt = Column(DateTime, nullable=False)
    trade_date = Column(String(8), nullable=False)  # 兼容字段

    # 买卖分类
    buy_sm_vol = Column(Integer)      # 小单买入量（手）
    buy_sm_amount = Column(Float)     # 小单买入额（万）
    sell_sm_vol = Column(Integer)
    sell_sm_amount = Column(Float)
    buy_md_vol = Column(Integer)      # 中单买入量
    buy_md_amount = Column(Float)
    sell_md_vol = Column(Integer)
    sell_md_amount = Column(Float)
    buy_lg_vol = Column(Integer)      # 大单买入量
    buy_lg_amount = Column(Float)
    sell_lg_vol = Column(Integer)
    sell_lg_amount = Column(Float)
    buy_elg_vol = Column(Integer)     # 特大单买入量
    buy_elg_amount = Column(Float)
    sell_elg_vol = Column(Integer)
    sell_elg_amount = Column(Float)

    # 净流入
    net_mf_vol = Column(Integer)      # 净流入量（手）
    net_mf_amount = Column(Float)     # 净流入额（万）

    created_at = Column(DateTime, server_default=func.now())

    # 关系
    stock = relationship("Stock", back_populates="moneyflows")

    # 约束与索引
    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_date_dt', name='uq_moneyflow_ts_code_date'),
        Index('ix_moneyflow_ts_code', 'ts_code'),
        Index('ix_moneyflow_trade_date_dt', 'trade_date_dt'),
        Index('ix_moneyflow_net_amount', 'net_mf_amount'),
    )
```

### 2. Alembic 迁移 (`alembic/versions/<rev>_create_moneyflow_table.py`)

```python
def upgrade():
    op.create_table(
        'moneyflow',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ts_code', sa.String(12), nullable=False),
        sa.Column('trade_date_dt', sa.DateTime(), nullable=False),
        sa.Column('trade_date', sa.String(8), nullable=False),
        # ... 所有买卖量/额字段
        sa.Column('buy_sm_vol', sa.Integer()),
        sa.Column('buy_sm_amount', sa.Float()),
        # ... 其他字段
        sa.Column('net_mf_vol', sa.Integer()),
        sa.Column('net_mf_amount', sa.Float()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # 创建唯一约束
    op.create_unique_constraint('uq_moneyflow_ts_code_date', 'moneyflow', ['ts_code', 'trade_date_dt'])

    # 创建索引
    op.create_index('ix_moneyflow_ts_code', 'moneyflow', ['ts_code'])
    op.create_index('ix_moneyflow_trade_date_dt', 'moneyflow', ['trade_date_dt'])
    op.create_index('ix_moneyflow_net_amount', 'moneyflow', ['net_mf_amount'])

def downgrade():
    op.drop_table('moneyflow')
```

### 3. Provider 扩展 (`app/core/crawling/tushare_provider.py`)

```python
class TushareProvider:
    async def fetch_moneyflow(
        self,
        ts_code: str = "",
        start_date: str = "",
        end_date: str = ""
    ) -> pd.DataFrame:
        """
        获取资金流向数据

        参数:
            ts_code: 股票代码（为空表示全市场）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        返回:
            DataFrame 包含 buy_sm_vol/sell_sm_vol 等字段
        """
        pro = ts.pro_api(settings.TUSHARE_TOKEN)

        df = pro.moneyflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return df

        # 列名标准化（Tushare 返回列名已符合，可跳过）
        # 确保 trade_date 转为 trade_date_dt
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df['trade_date'] = df['trade_date'].astype(str)

        return df
```

### 4. Repository (`app/repositories/moneyflow_repository.py`)

```python
from sqlalchemy import select, and_
from app.models.moneyflow_model import MoneyFlow

class MoneyFlowRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_stock(self, ts_code: str, start_date, end_date):
        """查询某股票资金流向"""
        query = select(MoneyFlow).where(
            and_(
                MoneyFlow.ts_code == ts_code,
                MoneyFlow.trade_date_dt >= start_date,
                MoneyFlow.trade_date_dt <= end_date
            )
        ).order_by(MoneyFlow.trade_date_dt.desc())
        return await self.session.execute(query).scalars().all()

    async def get_top_inflow(self, date, limit=20):
        """查询某日净流入最多的股票"""
        query = select(MoneyFlow).where(
            MoneyFlow.trade_date_dt == date
        ).order_by(MoneyFlow.net_mf_amount.desc()).limit(limit)
        return await self.session.execute(query).scalars().all()

    async def upsert_many(self, records: list[dict]):
        """批量插入（唯一约束去重）"""
        stmt = insert(MoneyFlow).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['ts_code', 'trade_date_dt']
        )
        await self.session.execute(stmt)
        await self.session.commit()
```

### 5. 抓取任务 (`app/jobs/tasks/fetch_moneyflow_task.py`)

```python
#!/usr/bin/env python3
"""
资金流向数据每日同步任务

执行时机: 每日 15:40（收盘后 10 分钟，晚于日线数据）
"""

import asyncio
from datetime import datetime, timedelta
from app.core.crawling.tushare_provider import TushareProvider
from app.repositories.moneyflow_repository import MoneyFlowRepository
from app.repositories.stock_repository import StockRepository

async def fetch_moneyflow_task():
    provider = TushareProvider()
    mf_repo = MoneyFlowRepository()
    stock_repo = StockRepository()

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    print(f"开始抓取 {yesterday} 资金流向数据...")

    # 方式 1: 全市场抓取（单次 API 调用）
    df = await provider.fetch_moneyflow(start_date=yesterday, end_date=yesterday)

    if not df.empty:
        records = df.to_dict('records')
        await mf_repo.upsert_many(records)
        print(f"写入 {len(records)} 条资金流向记录")
    else:
        print("无资金流向数据（可能为非交易日）")

if __name__ == "__main__":
    asyncio.run(fetch_moneyflow_task())
```

### 6. 验证脚本 (`scripts/verify_moneyflow.py`)

```python
#!/usr/bin/env python3
import psycopg2
from datetime import datetime, timedelta

def verify():
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # 1. 总行数
    cur.execute("SELECT COUNT(*) FROM moneyflow")
    print(f"moneyflow 总行数: {cur.fetchone()[0]:,}")

    # 2. 最新日期
    cur.execute("SELECT MAX(trade_date_dt) FROM moneyflow")
    latest = cur.fetchone()[0]
    print(f"最新数据日期: {latest}")

    # 3. 昨日数据量（应 ~5000）
    yesterday = (datetime.now() - timedelta(days=1)).date()
    cur.execute("SELECT COUNT(*) FROM moneyflow WHERE trade_date_dt = %s", (yesterday,))
    count = cur.fetchone()[0]
    print(f"昨日记录数: {count} (预期 ~5000)")

    # 4. 净流入分布
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE net_mf_amount > 0) as inflow,
            COUNT(*) FILTER (WHERE net_mf_amount < 0) as outflow,
            COUNT(*) FILTER (WHERE net_mf_amount = 0) as neutral
        FROM moneyflow
        WHERE trade_date_dt = %s
    """, (yesterday,))
    inflow, outflow, neutral = cur.fetchone()
    print(f"\n昨日资金流向: 净流入 {inflow} 只，净流出 {outflow} 只，中性 {neutral} 只")

    conn.close()

if __name__ == "__main__":
    verify()
```

---

## 验收标准

- [ ] `moneyflow` 表创建成功，为 TimescaleDB hypertable（由 WS0-03 保证）
- [ ] 唯一约束 `uq_moneyflow_ts_code_date` 生效
- [ ] `fetch_moneyflow_task.py` 可执行，能抓取全市场单日数据
- [ ] 数据量: 每日 ~5000 条（与股票数量匹配）
- [ ] `scripts/verify_moneyflow.py` 输出符合预期（行数、日期、资金流向分布）
- [ ] 重复执行幂等（唯一约束防止重复）
- [ ] 相关测试通过

---

## 交付物

- [ ] `app/models/moneyflow_model.py`
- [ ] Alembic 迁移脚本
- [ ] `app/core/crawling/tushare_provider.py` 扩展 `fetch_moneyflow`
- [ ] `app/repositories/moneyflow_repository.py`
- [ ] `app/jobs/tasks/fetch_moneyflow_task.py`
- [ ] `scripts/verify_moneyflow.py`
- [ ] `tests/test_moneyflow_repository.py`

---

**Trigger**: WS1-03 完成后启动（或并行）
**Estimated Time**: 0.5 天
