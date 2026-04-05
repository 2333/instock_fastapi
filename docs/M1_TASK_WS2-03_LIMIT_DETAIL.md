# Task: WS2-03 涨跌停明细接入 (limit_detail)

**Owner**: Agent E (Integration Specialist)
**Workstream**: WS-2 新接口扩展
**Priority**: P2 (细节补充)
**Estimated Effort**: 0.3 天
**Dependencies**: WS2-02
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `limit_list_d`（涨跌停明细）接口接入，创建 `limit_details` 表，记录每只涨跌停股票的明细信息（成交额/成交量/成交占比等）。

---

## 背景

`limit_list` 提供涨跌停汇总，`limit_list_d` 提供更细粒度的明细数据，用于:
- 分析涨停股票的资金推动特征
- 识别机构席位（若数据可用）
- 量化涨停质量（封单/成交比）

---

## 涉及表

| 表名 | 说明 |
|------|------|
| limit_details | 涨跌停明细（比 limit_stocks 更细） |

---

## 字段映射

Tushare `limit_list_d` 返回字段（常见）:

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 股票代码 |
| name | name | String(20) | 名称 |
| date | date | Date | 交易日期 |
| pct_chg | pct_chg | Float | 涨跌幅% |
| close | close | Float | 收盘价 |
| open | open | Float | 开盘价 |
| high | high | Float | 最高价 |
| low | low | Float | 最低价 |
| vol | vol | Float | 成交量（手） |
| amount | amount | Float | 成交额（元） |
| turnover_rate | turnover_rate | Float | 换手率% |
| float_share | float_share | Float | 流通股本（亿） |
| rise_limit | rise_limit | Float | 涨停价（计算得出） |

---

## 具体步骤

### 1. Model 定义

```python
class LimitDetail(Base):
    __tablename__ = "limit_details"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), nullable=False)
    trade_date = Column(Date, nullable=False)
    name = Column(String(20))
    pct_chg = Column(Float)      # 涨跌幅
    close = Column(Float)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    vol = Column(Float)          # 成交量（手）
    amount = Column(Float)       # 成交额
    turnover_rate = Column(Float)  # 换手率
    float_share = Column(Float)    # 流通股本
    rise_limit = Column(Float)     # 涨停价

    __table_args__ = (
        UniqueConstraint('ts_code', 'trade_date', name='uq_limit_detail_ts_code_date'),
        Index('ix_limit_detail_trade_date', 'trade_date'),
        Index('ix_limit_detail_ts_code', 'ts_code'),
    )
```

### 2. Provider 扩展

```python
async def fetch_limit_detail(
    self,
    trade_date: str = ""
) -> pd.DataFrame:
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    df = pro.limit_list_d(trade_date=trade_date)
    if df.empty:
        return df
    df['trade_date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df
```

### 3. 抓取任务

```python
async def fetch_limit_detail_task(trade_date=None):
    if trade_date is None:
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    df = await provider.fetch_limit_detail(trade_date=trade_date)
    if not df.empty:
        await repo.upsert_many(df.to_dict('records'))
        print(f"写入 {len(df)} 条涨跌停明细")
```

### 4. 验证

```python
# 对比 limit_stocks 与 limit_details 数量差异
cur.execute("""
    SELECT COUNT(*) FROM limit_stocks WHERE trade_date = CURRENT_DATE - 1
""")
stocks_cnt = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT ts_code) FROM limit_details WHERE trade_date = CURRENT_DATE - 1
""")
details_cnt = cur.fetchone()[0]

print(f"limit_stocks: {stocks_cnt}，limit_details: {details_cnt}（应基本一致）")
```

---

## 验收标准

- [ ] `limit_details` 表创建成功
- [ ] 抓取任务可执行
- [ ] 数据量与 limit_stocks 基本一致
- [ ] 相关测试通过

---

## 交付物

- [ ] Model + 迁移脚本
- [ ] Provider 扩展
- [ ] Repository
- [ ] 抓取任务
- [ ] 验证脚本
- [ ] 测试

---

**Trigger**: WS2-02 完成后
**Estimated Time**: 0.3 天
