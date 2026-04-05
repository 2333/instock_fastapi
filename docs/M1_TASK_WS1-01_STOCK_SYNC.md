# Task: WS1-01 股票代码同步与规范化

**Owner**: Agent C (Data Operations)
**Workstream**: WS-1 核心改造
**Priority**: P0 (数据接入前置)
**Estimated Effort**: 0.5 天
**Dependencies**: WS0-01 (Alembic 基线完成)
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

使用 `stock_basic` 接口全量拉取并同步股票基础信息表，统一 `ts_code`/`symbol`/`name` 字段，建立正确的主键与索引。

---

## 背景

股票代码体系是数据接入的基石:
- Tushare 使用 `ts_code` (带市场后缀，如 `000001.SZ`)
- 内部需同时支持 `ts_code` 与 `symbol` (纯数字，如 `000001`)
- `name` 字段随公司更名会变，历史数据需使用 `list_date` 时点的名称

目标:
- 表 `stocks` 包含所有历史及当前股票
- 主键: `ts_code` (稳定不变)
- 索引: `symbol`, `name`, `list_date`, `delist_date`
- 提供 `get_stock_by_symbol(symbol, date)` 查询方法

---

## 涉及表

| 表名 | 说明 |
|------|------|
| stocks | 股票基础信息（主数据） |

---

## 具体步骤

### 1. Model 定义 (`app/models/stock_model.py`)

```python
from sqlalchemy import Column, String, Date, DateTime, Boolean, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime

class Stock(Base):
    __tablename__ = "stocks"

    ts_code = Column(String(12), primary_key=True, nullable=False)  # 000001.SZ
    symbol = Column(String(6), nullable=False)  # 000001
    name = Column(String(20), nullable=False)  # 平安银行
    fullname = Column(String(50))  # 平安银行股份有限公司
    enname = Column(String(100))  # Ping An Bank Co., Ltd.
    cnspell = Column(String(20))  # pangxing
    area = Column(String(10))  # 深圳
    industry = Column(String(20))  # 银行
    industry_code = Column(String(10))  # 401010
    market = Column(String(10))  # 主板
    exchange = Column(String(10))  # SZSE
    curr_type = Column(String(10))  # CNY
    list_status = Column(String(1))  # L/D/P (上市/退市/暂停)
    list_date = Column(Date)  # 1991-04-03
    delist_date = Column(Date, nullable=True)  # None 或退市日期
    is_hs = Column(String(1))  # 是否沪深港通标的 N/H/S

    # 关系
    daily_bars = relationship("DailyBar", back_populates="stock")
    indicators = relationship("Indicator", back_populates="stock")

    # 索引
    __table_args__ = (
        Index('ix_stocks_symbol', 'symbol'),
        Index('ix_stocks_name', 'name'),
        Index('ix_stocks_list_date', 'list_date'),
        Index('ix_stocks_delist_date', 'delist_date'),
        Index('ix_stocks_industry', 'industry'),
    )
```

### 2. Alembic 迁移脚本

```bash
alembic revision -m "create-stocks-master-table"
```

编辑迁移脚本:

```python
def upgrade():
    op.create_table(
        'stocks',
        sa.Column('ts_code', sa.String(12), primary_key=True),
        sa.Column('symbol', sa.String(6), nullable=False),
        sa.Column('name', sa.String(20), nullable=False),
        sa.Column('fullname', sa.String(50)),
        sa.Column('enname', sa.String(100)),
        sa.Column('cnspell', sa.String(20)),
        sa.Column('area', sa.String(10)),
        sa.Column('industry', sa.String(20)),
        sa.Column('industry_code', sa.String(10)),
        sa.Column('market', sa.String(10)),
        sa.Column('exchange', sa.String(10)),
        sa.Column('curr_type', sa.String(10)),
        sa.Column('list_status', sa.String(1), nullable=False),
        sa.Column('list_date', sa.Date()),
        sa.Column('delist_date', sa.Date()),
        sa.Column('is_hs', sa.String(1)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
    )

    # 创建索引
    op.create_index('ix_stocks_symbol', 'stocks', ['symbol'])
    op.create_index('ix_stocks_name', 'stocks', ['name'])
    op.create_index('ix_stocks_list_date', 'stocks', ['list_date'])
    op.create_index('ix_stocks_delist_date', 'stocks', ['delist_date'])
    op.create_index('ix_stocks_industry', 'stocks', ['industry'])

def downgrade():
    op.drop_table('stocks')
```

### 3. 数据同步脚本 (`scripts/sync_stocks.py`)

```python
#!/usr/bin/env python3
"""
全量同步股票基础信息
每日执行一次（通常在开盘前）
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.core.crawling.tushare_provider import TushareProvider
from app.repositories.stock_repository import StockRepository

async def main():
    provider = TushareProvider()
    repo = StockRepository()

    print("正在从 Tushare 拉取股票基础信息...")
    df = await provider.fetch_stock_basic()

    print(f"获取到 {len(df)} 条记录，正在写入数据库...")
    await repo.upsert_many(df.to_dict('records'))

    print(f"同步完成。当前股票总数: {await repo.count()}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Repository 层 (`app/repositories/stock_repository.py`)

```python
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from app.models.stock_model import Stock

class StockRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_ts_code(self, ts_code: str) -> Stock:
        return self.session.get(Stock, ts_code)

    def get_by_symbol(self, symbol: str, date=None):
        """根据 symbol 查询股票，可指定日期（处理历史名称）"""
        query = select(Stock).where(Stock.symbol == symbol)
        if date:
            query = query.where(
                and_(
                    Stock.list_date <= date,
                    or_(
                        Stock.delist_date.is_(None),
                        Stock.delist_date >= date
                    )
                )
            )
        return self.session.execute(query).scalar_one_or_none()

    def get_all_active(self) -> list[Stock]:
        """获取所有当前上市股票"""
        return self.session.query(Stock).filter_by(list_status='L').all()

    async def upsert_many(self, records: list[dict]):
        """批量插入/更新"""
        # 使用 PostgreSQL ON CONFLICT DO UPDATE
        pass

    def count(self) -> int:
        return self.session.query(Stock).count()
```

### 5. 单元测试 `tests/test_stock_repository.py`

```python
def test_get_by_ts_code(session):
    repo = StockRepository(session)
    stock = repo.get_by_ts_code("000001.SZ")
    assert stock is not None
    assert stock.symbol == "000001"

def test_get_by_symbol_with_date(session):
    repo = StockRepository(session)
    # 假设有一只股票在 2020 年更名
    stock = repo.get_by_symbol("000001", date=datetime(2020, 1, 1))
    assert stock is not None
```

### 6. 集成到每日任务

在 `scripts/sync_all.py` 中调用:

```python
async def sync_stocks():
    """同步股票基础信息（每日一次）"""
    await StockRepository(session).full_sync()
```

---

## 验收标准

- [ ] `stocks` 表创建成功，主键为 `ts_code`
- [ ] 索引（symbol/name/list_date/delist_date/industry）创建成功
- [ ] `scripts/sync_stocks.py` 可执行，能从 Tushare 拉取全量数据
- [ ] 数据量验证: 当前上市股票 ~5000 只，历史总股票 > 5000
- [ ] 查询方法 `get_by_symbol(symbol, date)` 返回正确
- [ ] 相关测试通过

---

## 交付物

- [ ] `app/models/stock_model.py` (Stock model)
- [ ] Alembic 迁移脚本
- [ ] `app/repositories/stock_repository.py`
- [ ] `scripts/sync_stocks.py`
- [ ] `tests/test_stock_repository.py`
- [ ] 数据同步验证记录（行数、字段完整性）

---

**Trigger**: WS0-01 完成后启动
**Estimated Time**: 0.5 天
