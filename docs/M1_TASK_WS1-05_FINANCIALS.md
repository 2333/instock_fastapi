# Task: WS1-05 基本面数据同步 (financials)

**Owner**: Agent C (Data Operations)
**Workstream**: WS-1 核心改造
**Priority**: P1 (财务数据完整性)
**Estimated Effort**: 0.5 天
**Dependencies**: WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `fina_indicator` / `balancesheet` / `cashflow` / `income` 接口接入，创建财务事实表，支持季度/年度报告同步。

---

## 背景

基本面数据是基本面分析、估值模型的基石:
- 财务指标: 毛利率、ROE、资产负债率等
- 三大报表: 资产负债表、现金流量表、利润表
- 更新频率: 季度/年度（滞后 1-2 个月）

目标:
- 创建 `financial_indicators` 表（财务指标）
- 创建 `financial_statements` 表（原始报表，可选）
- 季度/年度数据全量同步
- 支持按股票、按报告期查询

---

## 涉及表

| 表名 | 说明 |
|------|------|
| financial_indicators | 财务指标（Tushare fina_indicator） |
| balancesheet | 资产负债表（可选） |
| cashflow | 现金流量表（可选） |
| income | 利润表（可选） |

---

## 字段映射: fina_indicator (财务指标)

Tushare 返回字段（常见）:

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 股票代码 |
| ann_date | ann_date | String(8) | 公告日期 |
| end_date | end_date | String(8) | 报告期（YYYYMMDD） |
| eps | eps | Float | 每股收益 |
| dt_eps | dt_eps | Float | 扣非每股收益 |
| revenue | revenue | Float | 营业收入（元） |
| profit | profit | Float | 净利润（元） |
| n_income | n_income | Float | 归属净利润 |
| roe | roe | Float | 净资产收益率（加权） |
| roe_wa | roe_wa | Float | ROE（加权平均） |
| roe_dt | roe_dt | Float | ROE（扣非） |
| gross_margin | gross_margin | Float | 毛利率 |
| ... | ... | ... | 其他字段（~80 列） |

**策略**: 由于字段过多，采用 JSON 存储原始记录 + 关键指标列结构化。

---

## 具体步骤

### 1. Model 定义 (`app/models/financial_model.py`)

```python
from sqlalchemy import Column, String, Float, Date, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

class FinancialIndicator(Base):
    __tablename__ = "financial_indicators"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), ForeignKey('stocks.ts_code'), nullable=False)
    ann_date = Column(Date)  # 公告日期
    end_date = Column(Date, nullable=False)  # 报告期末
    period = Column(String(6), nullable=False)  # 报告期标识: Q1/Q2/Q3/YEAR

    # 核心指标（结构化存储，便于查询）
    eps = Column(Float)           # 每股收益
    dt_eps = Column(Float)        # 扣非每股收益
    revenue = Column(Float)       # 营业收入（元）
    profit = Column(Float)        # 净利润
    n_income = Column(Float)      # 归属净利润
    roe = Column(Float)           # ROE（加权）
    gross_margin = Column(Float)  # 毛利率
    debt_to_assets = Column(Float)  # 资产负债率

    # 原始数据（JSON，保留全部字段）
    raw_data = Column(JSON)

    # 关系
    stock = relationship("Stock", back_populates="financials")

    # 约束与索引
    __table_args__ = (
        UniqueConstraint('ts_code', 'end_date', 'period', name='uq_financial_ts_code_enddate_period'),
        Index('ix_financial_ts_code', 'ts_code'),
        Index('ix_financial_end_date', 'end_date'),
        Index('ix_financial_period', 'period'),
    )
```

### 2. Alembic 迁移

```bash
alembic revision -m "create-financial-indicators-table"
```

迁移脚本:

```python
def upgrade():
    op.create_table(
        'financial_indicators',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ts_code', sa.String(12), nullable=False),
        sa.Column('ann_date', sa.Date()),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('period', sa.String(6), nullable=False),
        sa.Column('eps', sa.Float()),
        sa.Column('dt_eps', sa.Float()),
        sa.Column('revenue', sa.Float()),
        sa.Column('profit', sa.Float()),
        sa.Column('n_income', sa.Float()),
        sa.Column('roe', sa.Float()),
        sa.Column('gross_margin', sa.Float()),
        sa.Column('debt_to_assets', sa.Float()),
        sa.Column('raw_data', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_unique_constraint('uq_financial_ts_code_enddate_period', 'financial_indicators', ['ts_code', 'end_date', 'period'])
    op.create_index('ix_financial_ts_code', 'financial_indicators', ['ts_code'])
    op.create_index('ix_financial_end_date', 'financial_indicators', ['end_date'])

def downgrade():
    op.drop_table('financial_indicators')
```

### 3. Provider 扩展 (`app/core/crawling/tushare_provider.py`)

```python
class TushareProvider:
    async def fetch_financial_indicators(
        self,
        ts_code: str = "",
        period: str = "",  # 报告期: Q1/Q2/Q3/YEAR
        start_date: str = "",  # 公告期开始 YYYYMMDD
        end_date: str = ""     # 公告期结束
    ) -> pd.DataFrame:
        """
        获取财务指标数据

        参数:
            ts_code: 股票代码（空=全市场）
            period: 报告期类型
            start_date: 公告开始日期
            end_date: 公告结束日期

        返回:
            DataFrame 含 80+ 字段
        """
        pro = ts.pro_api(settings.TUSHARE_TOKEN)

        df = pro.fina_indicator(
            ts_code=ts_code,
            period=period,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return df

        # 日期转换
        df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')
        df['end_date'] = pd.to_datetime(df['end_date'], format='%Y%m%d')

        # 提取 period 标识（从 end_date 推导）
        df['period'] = df['end_date'].dt.strftime('%Y') + df['end_date'].dt.quarter.astype(str).replace('1', 'Q1').replace('2', 'Q2').replace('3', 'Q3').replace('4', 'Q4')

        return df
```

### 4. Repository (`app/repositories/financial_repository.py`)

```python
from sqlalchemy import select, and_
from datetime import datetime
from app.models.financial_model import FinancialIndicator

class FinancialRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_ts_code(
        self,
        ts_code: str,
        limit: int = 10
    ) -> list[FinancialIndicator]:
        """查询某股票最新 N 条财务指标"""
        query = select(FinancialIndicator).where(
            FinancialIndicator.ts_code == ts_code
        ).order_by(FinancialIndicator.end_date.desc()).limit(limit)
        return await self.session.execute(query).scalars().all()

    async def get_latest_by_period(
        self,
        period: str,  # e.g. "2024Q1"
        industry: str = None
    ) -> list[FinancialIndicator]:
        """查询指定报告期全市场财务指标"""
        query = select(FinancialIndicator).where(
            FinancialIndicator.period == period
        )

        if industry:
            # 需联表查询 stocks 表
            pass

        return await self.session.execute(query).scalars().all()

    async def upsert_many(self, records: list[dict]):
        """批量插入（唯一约束去重）"""
        stmt = insert(FinancialIndicator).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['ts_code', 'end_date', 'period'],
            set_={
                'eps': stmt.excluded.eps,
                'roe': stmt.excluded.roe,
                'raw_data': stmt.excluded.raw_data,
                'ann_date': stmt.excluded.ann_date,
            }
        )
        await self.session.execute(stmt)
        await self.session.commit()
```

### 5. 同步任务 (`app/jobs/tasks/sync_financials.py`)

```python
#!/usr/bin/env python3
"""
财务数据同步任务

执行时机: 每日凌晨（公告数据更新后）
"""

import asyncio
from datetime import datetime, timedelta
from app.core.crawling.tushare_provider import TushareProvider
from app.repositories.financial_repository import FinancialRepository
from app.repositories.stock_repository import StockRepository

async def sync_financials_task(period: str = None):
    """
    同步财务指标数据

    参数:
        period: 指定报告期（如 "2024Q1"），None 表示最新
    """
    provider = TushareProvider()
    repo = FinancialRepository()
    stock_repo = StockRepository()

    # 获取所有股票
    stocks = await stock_repo.get_all_active()
    print(f"开始同步 {len(stocks)} 只股票的财务数据...")

    # 确定报告期
    if period is None:
        # 自动推断最新报告期
        now = datetime.now()
        if now.month in [1, 2, 3]:
            period = f"{now.year}Q1"
        elif now.month in [4, 5, 6]:
            period = f"{now.year}Q2"
        ...

    # 批量抓取（全市场一次请求）
    df = await provider.fetch_financial_indicators(period=period)

    if not df.empty:
        records = df.to_dict('records')
        await repo.upsert_many(records)
        print(f"同步完成: {len(records)} 条财务指标记录")
    else:
        print("无新财务数据")

if __name__ == "__main__":
    asyncio.run(sync_financials_task())
```

### 6. 验证脚本 (`scripts/verify_financials.py`)

```python
#!/usr/bin/env python3
import psycopg2
from datetime import datetime

def verify():
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # 1. 总记录数
    cur.execute("SELECT COUNT(*) FROM financial_indicators")
    print(f"financial_indicators 总记录数: {cur.fetchone()[0]:,}")

    # 2. 报告期分布
    cur.execute("""
        SELECT period, COUNT(*) as cnt
        FROM financial_indicators
        GROUP BY period
        ORDER BY period DESC
        LIMIT 10
    """)
    print("\n最新报告期分布:")
    for period, cnt in cur.fetchall():
        print(f"  {period}: {cnt:,} 只股票")

    # 3. 关键指标缺失率
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(eps) as with_eps,
            COUNT(roe) as with_roe,
            COUNT(revenue) as with_revenue
        FROM financial_indicators
        WHERE period = '2024Q1'
    """)
    total, with_eps, with_roe, with_revenue = cur.fetchone()
    print(f"\n2024Q1 指标覆盖: EPS {with_eps/total*100:.1f}%, ROE {with_roe/total*100:.1f}%, Revenue {with_revenue/total*100:.1f}%")

    conn.close()

if __name__ == "__main__":
    verify()
```

---

## 验收标准

- [ ] `financial_indicators` 表创建成功，唯一约束生效
- [ ] `sync_financials_task.py` 可执行，能同步最新报告期数据
- [ ] 数据量: 每期 ~5000 条（全市场股票）
- [ ] 核心指标（eps/roe/revenue）覆盖率 ≥ 95%
- [ ] 幂等性验证通过
- [ ] 相关测试通过

---

## 交付物

- [ ] `app/models/financial_model.py`
- [ ] Alembic 迁移脚本
- [ ] `app/core/crawling/tushare_provider.py` 扩展 `fetch_financial_indicators`
- [ ] `app/repositories/financial_repository.py`
- [ ] `app/jobs/tasks/sync_financials.py`
- [ ] `scripts/verify_financials.py`
- [ ] `tests/test_financial_repository.py`

---

**Trigger**: WS1-01 完成后启动
**Estimated Time**: 0.5 天
