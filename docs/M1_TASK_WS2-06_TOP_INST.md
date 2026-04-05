# Task: WS2-06 龙虎榜数据接入 (top_list)

**Owner**: Agent E (Integration Specialist)
**Workstream**: WS-2 新接口扩展
**Priority**: P2 (机构行为分析)
**Estimated Effort**: 0.5 天
**Dependencies**: WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `top_list` 接口接入，创建 `top_inst` 表，同步龙虎榜机构买卖数据，用于分析机构资金动向。

---

## 背景

龙虎榜揭示机构席位买卖情况:
- 前 5 买入/卖出机构
- 买入/卖出金额
- 机构占比
- 判断机构意图（对倒/真实买入）

数据频率: 每日（出现异动时）

---

## 涉及表

| 表名 | 说明 |
|------|------|
| top_inst | 龙虎榜机构数据 |

---

## 字段映射

Tushare `top_list` 字段:

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 股票代码 |
| trade_date | trade_date | Date | 交易日期 |
| reason | reason | Text | 上榜原因 |
| buy_amount | buy_amount | Float | 机构合计买入额（万） |
| sell_amount | sell_amount | Float | 机构合计卖出额（万） |
| net_amount | net_amount | Float | 机构净买入（万） |

**注**: 详细机构列表（席位/金额）需额外接口 `top_inst_detail`。

---

## 具体步骤

### 1. Model 定义

```python
class TopInst(Base):
    __tablename__ = "top_inst"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), nullable=False)
    trade_date = Column(Date, nullable=False)
    reason = Column(Text)  # 上榜原因
    buy_amount = Column(Float)   # 机构买入额（万元）
    sell_amount = Column(Float)  # 机构卖出额（万元）
    net_amount = Column(Float)   # 机构净买入（万元）

    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_date', name='uq_top_inst_ts_code_date'),
        Index('ix_top_inst_trade_date', 'trade_date'),
        Index('ix_top_inst_ts_code', 'ts_code'),
    )
```

### 2. Alembic 迁移

```bash
alembic revision -m "create-top-institution-table"
```

### 3. Provider 扩展

```python
class TushareProvider:
    async def fetch_top_list(
        self,
        trade_date: str = ""
    ) -> pd.DataFrame:
        """获取龙虎榜机构汇总数据"""
        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        df = pro.top_list(trade_date=trade_date)
        if df.empty:
            return df
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        return df[['ts_code', 'trade_date', 'reason', 'buy_amount', 'sell_amount', 'net_amount']]
```

### 4. Repository & Task

```python
class TopInstRepository:
    async def get_by_date(self, trade_date):
        query = select(TopInst).where(TopInst.trade_date == trade_date)
        return await self.session.execute(query).scalars().all()

async def sync_top_inst_task(trade_date=None):
    if trade_date is None:
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    df = await provider.fetch_top_list(trade_date=trade_date)
    if not df.empty:
        await repo.upsert_many(df.to_dict('records'))
        print(f"写入龙虎榜数据: {len(df)} 条")
```

### 5. 验证

```python
def verify():
    cur.execute("SELECT COUNT(*) FROM top_inst WHERE trade_date = CURRENT_DATE - 1")
    print(f"昨日龙虎榜记录: {cur.fetchone()[0]} 条")
    cur.execute("SELECT AVG(net_amount) FROM top_inst WHERE trade_date = CURRENT_DATE - 1")
    print(f"平均机构净买入: {cur.fetchone()[0]:.2f} 万")
```

---

## 验收标准

- [ ] `top_inst` 表创建成功
- [ ] 可抓取指定日期龙虎榜数据
- [ ] 日增量 ~10-50 条（异动股票数量）
- [ ] 相关测试通过

---

## 交付物

- Model + 迁移
- Provider 扩展
- Repository
- 抓取任务
- 验证脚本
- 测试

---

**Trigger**: WS1-01 完成后
**Estimated Time**: 0.5 天
