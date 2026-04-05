# Task: WS2-02 涨跌停列表接入 (limit)

**Owner**: Agent E (Integration Specialist)
**Workstream**: WS-2 新接口扩展
**Priority**: P1 (市场情绪指标)
**Estimated Effort**: 0.3 天
**Dependencies**: WS0-01, WS0-02, WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `limit_list` 接口接入，创建 `limit_stocks` 表，每日同步涨跌停股票列表，用于市场情绪分析。

---

## 背景

涨跌停列表是市场情绪的直接体现:
- 涨停: 市场热点、板块轮动
- 跌停: 风险释放、恐慌程度
- 可识别连板股票（连续涨停）

数据更新频率: 每日（盘后）

---

## 涉及表

| 表名 | 说明 |
|------|------|
| limit_stocks | 涨跌停股票列表 |

---

## 字段映射

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 股票代码 |
| name | name | String(20) | 股票名称 |
| date | date | String(8) | 交易日期 |
| vol | vol | Float | 成交量（手） |
| amount | amount | Float | 成交额（元） |
| type | type | String(10) | 涨跌停类型: U=涨停 D=跌停 Z=炸板 |
| reason | reason | Text | 涨跌停原因（JSON/文本） |

---

## 具体步骤

### 1. Model 定义 (`app/models/limit_model.py`)

```python
from sqlalchemy import Column, String, Float, Date, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

class LimitStock(Base):
    __tablename__ = "limit_stocks"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), ForeignKey('stocks.ts_code'), nullable=False)
    trade_date = Column(Date, nullable=False)
    name = Column(String(20), nullable=False)
    vol = Column(Float)       # 成交量（手）
    amount = Column(Float)    # 成交额（元）
    limit_type = Column(String(10), nullable=False)  # U/D/Z
    reason = Column(Text)     # 涨跌停原因

    # 关系
    stock = relationship("Stock")

    # 约束
    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_date', name='uq_limit_ts_code_date'),
        Index('ix_limit_trade_date', 'trade_date'),
        Index('ix_limit_type', 'limit_type'),
        Index('ix_limit_ts_code', 'ts_code'),
    )
```

### 2. Alembic 迁移

```bash
alembic revision -m "create-limit-stocks-table"
```

### 3. Provider 扩展

```python
class TushareProvider:
    async def fetch_limit_list(
        self,
        trade_date: str = "",  # YYYYMMDD，空=最新
        limit_type: str = ""   # U/D/Z，空=全部
    ) -> pd.DataFrame:
        """
        获取涨跌停列表

        参数:
            trade_date: 交易日期
            limit_type: 类型筛选（U=涨停 D=跌停 Z=炸板）

        返回:
            DataFrame: ts_code/name/date/vol/amount/type/reason
        """
        pro = ts.pro_api(settings.TUSHARE_TOKEN)

        df = pro.limit_list(
            trade_date=trade_date,
            limit_type=limit_type
        )

        if df.empty:
            return df

        # 标准化
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df.rename(columns={'type': 'limit_type'}, inplace=True)

        return df[['ts_code', 'name', 'trade_date', 'vol', 'amount', 'limit_type', 'reason']]
```

### 4. Repository

```python
class LimitStockRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_date(self, trade_date: str) -> list[LimitStock]:
        """查询某日涨跌停列表"""
        query = select(LimitStock).where(LimitStock.trade_date == trade_date)
        return await self.session.execute(query).scalars().all()

    async def get_continuous_limit(self, ts_code: str, days: int = 3) -> bool:
        """查询是否连续 N 日涨停"""
        # 需检查最近 N 日是否存在涨停记录
        pass

    async def upsert_many(self, records: list[dict]):
        stmt = insert(LimitStock).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['ts_code', 'trade_date']
        )
        await self.session.execute(stmt)
        await self.session.commit()
```

### 5. 抓取任务

```python
#!/usr/bin/env python3
async def fetch_limit_task(trade_date=None):
    provider = TushareProvider()
    repo = LimitStockRepository()

    if trade_date is None:
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    df = await provider.fetch_limit_list(trade_date=trade_date)

    if not df.empty:
        await repo.upsert_many(df.to_dict('records'))
        print(f"写入 {len(df)} 条涨跌停记录")

    # 统计: 涨停数、跌停数、炸板数
    stats = df['limit_type'].value_counts().to_dict()
    print(f"涨停: {stats.get('U',0)}，跌停: {stats.get('D',0)}，炸板: {stats.get('Z',0)}")
```

### 6. 验证

```python
def verify():
    cur.execute("SELECT COUNT(*) FROM limit_stocks WHERE trade_date = CURRENT_DATE - 1")
    print(f"昨日涨跌停记录数: {cur.fetchone()[0]}")

    cur.execute("""
        SELECT limit_type, COUNT(*) FROM limit_stocks
        WHERE trade_date = CURRENT_DATE - 1
        GROUP BY limit_type
    """)
    for t, cnt in cur.fetchall():
        print(f"  {t}: {cnt}")
```

---

## 验收标准

- [ ] `limit_stocks` 表创建成功
- [ ] `fetch_limit_task.py` 可执行，能抓取昨日数据
- [ ] 数据量: 每日 50-200 条（正常交易日）
- [ ] 统计输出符合市场观察（涨停数通常在 50-100 只）
- [ ] 相关测试通过

---

## 交付物

- [ ] `app/models/limit_model.py`
- [ ] Alembic 迁移脚本
- [ ] Provider 扩展
- [ ] Repository
- [ ] 抓取任务
- [ ] 验证脚本
- [ ] 测试

---

**Trigger**: WS1-02 完成后启动
**Estimated Time**: 0.3 天
