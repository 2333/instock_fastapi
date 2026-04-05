# Task: WS0-04 通用行情接口抽象 (pro_bar)

**Owner**: Agent B (Provider/Task Specialist)
**Workstream**: WS-0 基础设施
**Priority**: P0 (阻塞 WS-1 主抓取任务切换)
**Estimated Effort**: 1 天
**Dependencies**: 无（可独立开发）
**Status**: Ready to assign (等待 M1 启动信号)

---

## 任务描述

实现 `fetch_pro_bar` 统一行情数据获取入口，支持多资产类型（E/I/FT/O/FD），为后续 `fetch_daily_task` 切换提供统一抽象。

---

## 背景

当前问题:
- 股票、指数、ETF 各走不同的获取路径
- 字段映射散落在各个 crawler 中
- 扩展新资产类型需改多处代码

目标:
- 单一入口 `pro_bar` 覆盖所有资产类型
- 返回标准化 DataFrame（列名统一）
- 内部按 asset 类型路由到 Tushare 不同接口

---

## 涉及接口（Tushare）

| asset | 接口 | 说明 |
|-------|------|------|
| E (股票) | `pro.daily()` | 日线行情 |
| I (指数) | `pro.index_daily()` | 指数日线 |
| FT (期货) | `pro.fut_daily()` | 期货日线（后续） |
| O (期权) | `pro.opt_daily()` | 期权日线（后续） |
| FD (基金) | `pro.fund_daily()` | 基金日线（后续） |

当前阶段优先实现 E 和 I。

---

## 具体步骤

### 1. 创建 `app/services/pro_bar.py`

```python
"""
通用行情接口抽象 (pro_bar)

统一所有资产类型的日线数据获取，返回标准化 DataFrame:
- ts_code: 标的代码
- trade_date: 交易日（字符串 YYYYMMDD）
- open/high/low/close: 价格
- vol: 成交量（手）
- amount: 成交额（元）
- adj_factor: 复权因子（如适用）
"""

from typing import Optional, List
import pandas as pd
from app.core.crawling.tushare_provider import TushareProvider
from app.config import get_settings

class ProBarService:
    """通用行情服务"""

    def __init__(self):
        self.provider = TushareProvider()
        self.settings = get_settings()

    async def fetch_pro_bar(
        self,
        ts_code: str,
        asset: str = "E",  # E/I/FT/O/FD
        freq: str = "D",   # D/W/M/min
        adj: Optional[str] = None,  # qfq/hfq/None (仅股票)
        start_date: str = "",
        end_date: str = "",
        ma: Optional[List[int]] = None,  # 移动平均周期列表
        factors: Optional[List[str]] = None,  # 额外因子列表
    ) -> pd.DataFrame:
        """
        获取通用行情数据

        参数:
            ts_code: 标的代码（如 000001.SZ）
            asset: 资产类型 E=股票 I=指数 FT=期货 O=期权 FD=基金
            freq: 频率 D=日 W=周 M=月
            adj: 复权方式（仅股票）
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            ma: 移动平均周期列表，如 [5, 10, 20]
            factors: 额外因子，如 ['macd', 'rsi']

        返回:
            pandas.DataFrame 标准化列:
            - ts_code
            - trade_date (datetime 或 str)
            - open, high, low, close
            - vol, amount
            - adj_factor (如有)
            - ma_5, ma_10, ... (如请求)
            - macd, rsi, ... (如请求)
        """
        # 调用 provider
        df = await self.provider.fetch_pro_bar(
            ts_code=ts_code,
            asset=asset,
            freq=freq,
            adj=adj,
            start_date=start_date,
            end_date=end_date,
            ma=ma,
            factors=factors,
        )

        # 标准化列名（provider 已处理，此处二次确认）
        expected_cols = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount']
        for col in expected_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # 类型转换
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        numeric_cols = ['open', 'high', 'low', 'close', 'vol', 'amount']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

# 全局单例
pro_bar_service = ProBarService()
```

### 2. 扩展 `TushareProvider` 实现 `fetch_pro_bar`

编辑 `app/core/crawling/tushare_provider.py`:

```python
class TushareProvider:
    async def fetch_pro_bar(
        self,
        ts_code: str,
        asset: str = "E",
        freq: str = "D",
        adj: Optional[str] = None,
        start_date: str = "",
        end_date: str = "",
        ma: Optional[List[int]] = None,
        factors: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        统一行情获取入口

        路由逻辑:
        - asset=E → pro.daily()
        - asset=I → pro.index_daily()
        - asset=FT → pro.fut_daily()
        - ...
        """
        import tushare as ts
        from app.config import get_settings

        settings = get_settings()
        pro = ts.pro_api(settings.TUSHARE_TOKEN)

        # 参数映射
        params = {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
        }
        if asset == "E":
            df = pro.daily(**params)
            # 复权处理
            if adj in ("qfq", "hfq"):
                # 调用 adj_factor 接口或本地计算
                pass
        elif asset == "I":
            df = pro.index_daily(**params)
        elif asset == "FT":
            df = pro.fut_daily(**params)
        elif asset == "O":
            df = pro.opt_daily(**params)
        elif asset == "FD":
            df = pro.fund_daily(**params)
        else:
            raise ValueError(f"Unsupported asset type: {asset}")

        if df.empty:
            return df

        # 标准化列名（不同接口返回字段不同）
        column_mapping = {
            # 股票/指数
            "trade_date": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "vol",
            "amount": "amount",
            # 期货/期权可能有不同命名，需映射
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 计算移动平均（如请求）
        if ma:
            for period in ma:
                df[f"ma_{period}"] = df['close'].rolling(period).mean()

        # 计算技术因子（如请求）
        if factors:
            # 可集成 TA-Lib 或自实现
            pass

        return df
```

### 3. 编写单元测试

创建 `tests/test_pro_bar.py`:

```python
import pytest
from app.services.pro_bar import pro_bar_service

@pytest.mark.asyncio
async def test_fetch_pro_bar_stock():
    df = await pro_bar_service.fetch_pro_bar(
        ts_code="000001.SZ",
        asset="E",
        start_date="20260101",
        end_date="20260131",
    )
    assert not df.empty
    assert {'ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount'}.issubset(df.columns)

@pytest.mark.asyncio
async def test_fetch_pro_bar_index():
    df = await pro_bar_service.fetch_pro_bar(
        ts_code="000001.SH",
        asset="I",
        start_date="20260101",
        end_date="20260131",
    )
    assert not df.empty
    assert df['ts_code'].iloc[0] == "000001.SH"
```

### 4. 集成到抓取任务

待 WS1-16 执行时，修改 `app/jobs/tasks/fetch_daily_task.py`:

```python
# 旧: 直接调用 provider.fetch_daily()
# 新: 调用 pro_bar_service.fetch_pro_bar()
from app.services.pro_bar import pro_bar_service

async def fetch_daily_task():
    # 获取股票列表
    stocks = await stock_repository.get_all()
    for stock in stocks:
        df = await pro_bar_service.fetch_pro_bar(
            ts_code=stock.ts_code,
            asset="E",
            start_date=yesterday_str,
            end_date=yesterday_str,
        )
        # 写入 daily_bars 表
        await daily_bar_repository.upsert_many(df.to_dict('records'))
```

---

## 验收标准

- [ ] `tests/test_pro_bar.py` 通过（股票和指数场景）
- [ ] 返回 DataFrame 包含必需列（ts_code/trade_date/open/high/low/close/vol/amount）
- [ ] `trade_date` 转为 datetime 类型
- [ ] 移动平均与因子计算可选且正确
- [ ] 错误处理：不支持的 asset 类型抛出 ValueError

---

## 交付物

- [ ] `app/services/pro_bar.py` 实现
- [ ] `app/core/crawling/tushare_provider.py` 扩展 `fetch_pro_bar` 方法
- [ ] `tests/test_pro_bar.py` 单元测试
- [ ] `docs/TUSHARE_PROVIDER.md`（可选，记录 asset 路由表）

---

**注意**: 此任务为 WS-0 最后一项，完成后即可解锁 WS-1 的主抓取任务切换（WS1-16）。
