# Task: WS2-05 备用基础信息接入 (bak_basic)

**Owner**: Agent E (Integration Specialist)
**Workstream**: WS-2 新接口扩展
**Priority**: P2 (数据完整性)
**Estimated Effort**: 0.3 天
**Dependencies**: WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `bak_basic` 接口接入，创建 `stocks_bak` 表，同步历史股票基础信息（已退市/更名股票的历史快照）。

---

## 背景

`stock_basic` 仅返回当前上市或最近状态，历史更名/退市信息存储在 `bak_basic`:
- 记录股票历史名称变更
- 保留已退市股票信息
- 辅助历史数据回溯

---

## 涉及表

| 表名 | 说明 |
|------|------|
| stocks_bak | 股票基础信息历史快照 |

---

## 字段映射

主要字段:
- `ts_code` / `symbol` / `name` (历史名称)
- `list_date` / `delist_date`
- `change_reason` (变更原因: 退市/更名/其他)

---

## 具体步骤

### 1. Model 定义

```python
class StockHistory(Base):
    __tablename__ = "stocks_bak"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), nullable=False)
    symbol = Column(String(6), nullable=False)
    name = Column(String(20), nullable=False)  # 历史名称
    list_date = Column(Date)
    delist_date = Column(Date)
    change_reason = Column(String(50))  # 变更原因
    valid_from = Column(Date)  # 此快照生效日期
    valid_to = Column(Date, nullable=True)  # 失效日期（当前为 NULL）

    __table_args__ = (
        Index('ix_stocks_bak_ts_code', 'ts_code'),
        Index('ix_stocks_bak_name', 'name'),
    )
```

### 2. 迁移脚本

```bash
alembic revision -m "create-stocks-bak-table"
```

### 3. Provider

```python
async def fetch_bak_basic(
    self,
    ts_code: str = "",
    start_date: str = "",
    end_date: str = ""
) -> pd.DataFrame:
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    df = pro.bak_basic(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date
    )
    if df.empty:
        return df
    df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d')
    df['delist_date'] = pd.to_datetime(df['delist_date'], format='%Y%m%d')
    return df
```

### 4. 同步任务

```python
async def sync_stocks_bak():
    """全量同步历史股票快照（一次性任务）"""
    df = await provider.fetch_bak_basic()
    await repo.upsert_many(df.to_dict('records'))
```

---

## 验收标准

- [ ] 表创建成功
- [ ] 数据量: ~10,000 条（历史股票快照）
- [ ] 相关测试通过

---

## 交付物

- Model + 迁移
- Provider 扩展
- Repository
- 同步脚本
- 测试

---

**Trigger**: WS1-01 完成后
**Estimated Time**: 0.3 天
