from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional
from decimal import Decimal


STRATEGIES = [
    {
        "name": "enter",
        "display_name": "放量上涨",
        "description": "成交量放大的上涨股票",
    },
    {
        "name": "keep_increasing",
        "display_name": "均线多头",
        "description": "均线多头排列的股票",
    },
    {
        "name": "parking_apron",
        "display_name": "停机坪",
        "description": "涨停后调整的股票",
    },
    {
        "name": "backtrace_ma250",
        "display_name": "回踩年线",
        "description": "回踩250日均线的股票",
    },
    {
        "name": "breakthrough_platform",
        "display_name": "突破平台",
        "description": "突破整理平台的股票",
    },
    {
        "name": "turtle_trade",
        "display_name": "海龟交易法则",
        "description": "海龟交易策略选股",
    },
    {
        "name": "high_tight_flag",
        "display_name": "高而窄的旗形",
        "description": "高而窄的旗形形态",
    },
    {
        "name": "climax_limitdown",
        "display_name": "放量跌停",
        "description": "放量跌停的股票",
    },
    {
        "name": "low_backtrace_increase",
        "display_name": "无大幅回撤",
        "description": "60日内无大幅回撤的股票",
    },
    {
        "name": "low_atr",
        "display_name": "低ATR成长",
        "description": "低波动率高成长股票",
    },
]


class StrategyService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def get_strategy_list() -> List[dict]:
        return STRATEGIES

    async def run_strategy(self, strategy_name: str, date: Optional[str]):
        return {"status": "success", "strategy": strategy_name, "count": 0}

    async def get_results(
        self, strategy_name: Optional[str] = None, date: Optional[str] = None, limit: int = 100
    ):
        query = text("""
            SELECT 
                sr.id,
                sr.trade_date as date,
                sr.score,
                sr.signal,
                sr.details,
                s.name,
                s.symbol as code,
                s.ts_code,
                db.close as new_price,
                db.pct_chg as change_rate,
                st.name as strategy_name
            FROM strategy_results sr
            LEFT JOIN stocks s ON sr.ts_code = s.ts_code
            LEFT JOIN strategies st ON sr.strategy_id = st.id
            LEFT JOIN daily_bars db ON sr.ts_code = db.ts_code AND sr.trade_date = db.trade_date
            ORDER BY sr.score DESC, sr.trade_date DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"limit": limit})
        return [dict(row._mapping) for row in result.fetchall()]
