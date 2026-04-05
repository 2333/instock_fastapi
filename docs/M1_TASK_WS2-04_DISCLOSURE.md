# Task: WS2-04 公告数据接入 (disclosure)

**Owner**: Agent E (Integration Specialist)
**Workstream**: WS-2 新接口扩展
**Priority**: P2 (公告信息)
**Estimated Effort**: 0.5 天
**Dependencies**: WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

实现 Tushare `disclosure` 接口接入，创建 `disclosures` 表，同步上市公司公告信息（财报、重大事项等）。

---

## 背景

公告数据是事件驱动策略的重要来源:
- 财报披露（定期报告）
- 重大事项（重组、增发、股权变动）
- 股价敏感信息

可用于:
- 事件回测
- 公告提醒（API 推送）
- 基本面分析

---

## 涉及表

| 表名 | 说明 |
|------|------|
| disclosures | 公告信息表 |

---

## 字段映射

Tushare `disclosure` 接口字段:

| Tushare 字段 | 列名 | 类型 | 说明 |
|--------------|------|------|------|
| ts_code | ts_code | String(12) | 股票代码 |
| name | name | String(20) | 名称 |
| ann_date | ann_date | Date | 公告日期 |
| title | title | Text | 公告标题 |
| digest | digest | Text | 摘要 |
| type | type | String(20) | 公告类型 |
| url | url | String(200) | 公告链接 |

---

## 具体步骤

### 1. Model 定义

```python
class Disclosure(Base):
    __tablename__ = "disclosures"

    id = Column(Integer, primary_key=True)
    ts_code = Column(String(12), nullable=False)
    name = Column(String(20))
    ann_date = Column(Date, nullable=False)
    title = Column(Text, nullable=False)
    digest = Column(Text)
    type = Column(String(20))  # 公告类型: 财报/重大事项/其他
    url = Column(String(200))

    __table_args__ = (
        Index('ix_disclosures_ann_date', 'ann_date'),
        Index('ix_disclosures_ts_code', 'ts_code'),
        Index('ix_disclosures_type', 'type'),
    )
```

### 2. Alembic 迁移

```bash
alembic revision -m "create-disclosures-table"
```

### 3. Provider

```python
async def fetch_disclosures(
    self,
    start_date: str = "",
    end_date: str = "",
    ts_code: str = ""
) -> pd.DataFrame:
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    df = pro.disclosure(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code
    )
    if df.empty:
        return df
    df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')
    return df[['ts_code', 'name', 'ann_date', 'title', 'digest', 'type', 'url']]
```

### 4. Repository & Task

```python
class DisclosureRepository:
    async def get_by_date_range(self, start_date, end_date):
        query = select(Disclosure).where(
            Disclosure.ann_date >= start_date,
            Disclosure.ann_date <= end_date
        )
        return await self.session.execute(query).scalars().all()

async def sync_disclosures_task(days=7):
    """同步最近 N 天的公告"""
    end = datetime.now()
    start = end - timedelta(days=days)

    df = await provider.fetch_disclosures(
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d")
    )

    if not df.empty:
        await repo.upsert_many(df.to_dict('records'))
```

---

## 验收标准

- [ ] 表创建成功
- [ ] 可抓取最近 7 天公告
- [ ] 日增量 ~100-500 条（估算）
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
