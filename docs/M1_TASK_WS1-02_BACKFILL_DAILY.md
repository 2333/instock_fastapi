# Task: WS1-02 日线数据回填与增量同步

**Owner**: Agent C (Data Operations)
**Workstream**: WS-1 核心改造
**Priority**: P0 (历史数据迁移)
**Estimated Effort**: 1 天
**Dependencies**: WS0-01, WS0-02, WS1-01
**Status**: Ready to assign (M1 启动后执行)

---

## 任务描述

执行日线数据（daily_bars）全量回填与增量同步，将历史数据迁移至新表结构，并配置每日增量抓取任务。

---

## 背景

M1 数据层底座的核心目标是:
- 将历史日线数据从旧格式迁移到新 schema
- 建立稳定可靠的增量同步机制
- 保证数据完整性与一致性

数据量估算:
- 全市场股票约 5000 只
- 每只股票约 2000 个交易日（10 年）
- 总行数 ~1000 万（需分批迁移）

---

## 具体步骤

### 1. 数据回填策略

由于数据量较大（千万级），采用分批迁移:

```python
# scripts/backfill_daily_bars.py

import asyncio
from tqdm import tqdm
from app.core.crawling.tushare_provider import TushareProvider
from app.repositories.daily_bar_repository import DailyBarRepository
from app.models.stock_model import Stock

BATCH_SIZE = 100  # 每批股票数量
HISTORY_YEARS = 10

async def backfill():
    provider = TushareProvider()
    repo = DailyBarRepository()

    # 获取所有股票代码
    stocks = await StockRepository().get_all_active()
    total_stocks = len(stocks)

    print(f"开始回填 {total_stocks} 只股票的历史日线数据...")

    for i in tqdm(range(0, total_stocks, BATCH_SIZE)):
        batch = stocks[i:i+BATCH_SIZE]

        tasks = []
        for stock in batch:
            # 计算起止日期
            start_date = f"{datetime.now().year - HISTORY_YEARS}0101"
            end_date = datetime.now().strftime("%Y%m%d")

            tasks.append(
                provider.fetch_daily(
                    ts_code=stock.ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
            )

        # 并发抓取
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 写入数据库
        all_records = []
        for df in results:
            if isinstance(df, pd.DataFrame) and not df.empty:
                all_records.extend(df.to_dict('records'))

        if all_records:
            await repo.upsert_many(all_records)

        print(f"已处理 {min(i+BATCH_SIZE, total_stocks)}/{total_stocks} 只股票")

    print("回填完成!")
```

### 2. 增量同步配置

创建每日抓取任务 `app/jobs/tasks/fetch_daily_task.py`:

```python
#!/usr/bin/env python3
"""
每日日线数据抓取任务

执行时机:
- 交易日收盘后 (例如 15:30)
- 或按需手动触发

流程:
1. 获取所有上市股票列表
2. 对每只股票抓取昨日数据
3. 写入 daily_bars 表（自动去重）
"""

import asyncio
from datetime import datetime, timedelta
from app.core.crawling.tushare_provider import TushareProvider
from app.repositories.daily_bar_repository import DailyBarRepository
from app.repositories.stock_repository import StockRepository

async def fetch_daily_task():
    provider = TushareProvider()
    daily_repo = DailyBarRepository()
    stock_repo = StockRepository()

    # 计算昨日日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    print(f"开始抓取 {yesterday} 的日线数据...")

    # 获取所有上市股票
    stocks = await stock_repo.get_all_active()
    print(f"股票数量: {len(stocks)}")

    success_count = 0
    fail_count = 0

    for stock in stocks:
        try:
            df = await provider.fetch_daily(
                ts_code=stock.ts_code,
                start_date=yesterday,
                end_date=yesterday
            )

            if not df.empty:
                await daily_repo.upsert_many(df.to_dict('records'))
                success_count += 1
            else:
                print(f"警告: {stock.ts_code} 无数据")
                fail_count += 1

        except Exception as e:
            print(f"错误: {stock.ts_code} 抓取失败: {e}")
            fail_count += 1

    print(f"完成: 成功 {success_count}，失败 {fail_count}")

    # 写入抓取任务日志
    await log_fetch_task(
        date=yesterday,
        total=len(stocks),
        success=success_count,
        fail=fail_count
    )

async def log_fetch_task(date: str, total: int, success: int, fail: int):
    """记录抓取任务执行日志"""
    # 写入 fetch_logs 表
    pass

if __name__ == "__main__":
    asyncio.run(fetch_daily_task())
```

### 3. 定时任务配置

使用 `cron` 或 `schedule` 库:

**方式 A: Cron**
```bash
# crontab -e
30 15 * * 1-5 cd /path/to/instock_fastapi && .venv/bin/python app/jobs/tasks/fetch_daily_task.py >> logs/cron.log 2>&1
# 每个交易日 15:30 执行（A股收盘后）
```

**方式 B: APScheduler (应用内)**

```python
# app/jobs/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.jobs.tasks.fetch_daily_task import fetch_daily_task

scheduler = AsyncIOScheduler()

def start_scheduler():
    # 每个交易日 15:30 执行
    scheduler.add_job(
        fetch_daily_task,
        trigger='cron',
        day_of_week='mon-fri',
        hour=15,
        minute=30
    )
    scheduler.start()
```

### 4. 幂等性设计

`upsert_many` 实现:

```python
# app/repositories/daily_bar_repository.py

async def upsert_many(self, records: list[dict]):
    """批量插入或更新（基于 ts_code + trade_date_dt 唯一约束）"""
    if not records:
        return

    # 使用 PostgreSQL ON CONFLICT
    stmt = insert(DailyBar).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=['ts_code', 'trade_date_dt'],
        set_={
            'open': stmt.excluded.open,
            'high': stmt.excluded.high,
            'low': stmt.excluded.low,
            'close': stmt.excluded.close,
            'vol': stmt.excluded.vol,
            'amount': stmt.excluded.amount,
            'updated_at': func.now(),
        }
    )

    await self.session.execute(stmt)
    await self.session.commit()
```

### 5. 数据验证

回填完成后验证:

```python
# scripts/verify_backfill.py

import psycopg2
from datetime import datetime

def verify():
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # 1. 总行数
    cur.execute("SELECT COUNT(*) FROM daily_bars")
    total = cur.fetchone()[0]
    print(f"daily_bars 总行数: {total:,}")

    # 2. 时间范围
    cur.execute("SELECT MIN(trade_date_dt), MAX(trade_date_dt) FROM daily_bars")
    min_date, max_date = cur.fetchone()
    print(f"时间范围: {min_date} ~ {max_date}")

    # 3. 股票覆盖
    cur.execute("SELECT COUNT(DISTINCT ts_code) FROM daily_bars")
    stock_count = cur.fetchone()[0]
    print(f"覆盖股票数: {stock_count}")

    # 4. 缺失交易日检查
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT ts_code, trade_date_dt
            FROM daily_bars
            WHERE trade_date_dt >= CURRENT_DATE - INTERVAL '10 years'
        ) d
        RIGHT JOIN stocks s ON d.ts_code = s.ts_code
        WHERE d.ts_code IS NULL
    """)
    missing = cur.fetchone()[0]
    print(f"缺失股票-日期组合: {missing}")

    conn.close()
```

### 6. 错误处理与重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class TushareProvider:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            # 调用 Tushare API
            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            if "频繁" in str(e):
                await asyncio.sleep(60)  # 频率限制等待 1 分钟
            raise
```

---

## 验收标准

- [ ] `daily_bars` 表数据量 ≥ 1000 万行（10 年全市场）
- [ ] 每只股票交易日数量在合理范围（2500±500 天）
- [ ] 时间范围覆盖完整（ earliest ~ latest）
- [ ] 增量任务 `fetch_daily_task.py` 可执行，能抓取昨日数据
- [ ] 幂等性验证：重复执行不会产生重复数据
- [ ] 错误重试机制工作正常（模拟失败可重试）
- [ ] 相关测试通过

---

## 交付物

- [ ] `scripts/backfill_daily_bars.py`（全量回填）
- [ ] `app/jobs/tasks/fetch_daily_task.py`（每日增量）
- [ ] `app/repositories/daily_bar_repository.py`（upsert 实现）
- [ ] `scripts/verify_backfill.py`（数据验证）
- [ ] `tests/test_daily_bar_repository.py`（幂等性测试）
- [ ] `docs/BACKFILL_REPORT.md`（回填报告）

---

**Trigger**: WS1-01 完成后启动
**Estimated Time**: 1 天（含验证）
