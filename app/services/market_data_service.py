from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class MarketDataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_trade_date(
        self, target_date: str | None, table_name: str = "daily_bars"
    ) -> str | None:
        if table_name not in {
            "daily_bars",
            "fund_flows",
            "stock_block_trades",
            "stock_tops",
            "north_bound_funds",
        }:
            raise ValueError(f"unsupported trade date table: {table_name}")
        if target_date:
            result = await self.db.execute(
                text(
                    f"""
                    SELECT MAX(trade_date) as resolved_date
                    FROM {table_name}
                    WHERE trade_date <= :target_date
                    """
                ),
                {"target_date": target_date},
            )
        else:
            result = await self.db.execute(
                text(f"SELECT MAX(trade_date) as resolved_date FROM {table_name}")
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def get_fund_flow_rank(self, date: str | None, limit: int = 50) -> list[dict]:
        """获取资金流排行"""
        date = await self._resolve_trade_date(date, "fund_flows")
        if not date:
            return []

        query = text("""
            SELECT
                s.symbol as code,
                s.name,
                db.close as close,
                db.pct_chg as change_rate,
                f.net_amount_main as main_net_inflow,
                f.net_amount_hf as huge_net_inflow,
                f.net_amount_zz as mid_net_inflow,
                f.net_amount_xd as small_net_inflow,
                f.trade_date
            FROM fund_flows f
            INNER JOIN stocks s ON split_part(f.ts_code, '.', 1) = s.symbol
            INNER JOIN daily_bars db ON s.ts_code = db.ts_code AND db.trade_date = f.trade_date
            WHERE f.trade_date = :date
            ORDER BY f.net_amount_main DESC NULLS LAST
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"date": date, "limit": limit})
        return [row._mapping for row in result.fetchall()]

    async def get_block_trades(self, date: str | None, limit: int = 50) -> list[dict]:
        """获取大宗交易数据"""
        date = await self._resolve_trade_date(date, "stock_block_trades")
        if not date:
            return []

        query = text("""
            SELECT
                split_part(bt.ts_code, '.', 1) as code,
                COALESCE(s.name, '') as name,
                bt.avg_price as price,
                bt.total_volume as vol,
                bt.total_amount as amount,
                bt.premium_rate,
                bt.trade_date
            FROM stock_block_trades bt
            LEFT JOIN stocks s ON split_part(bt.ts_code, '.', 1) = s.symbol
            WHERE bt.trade_date = :date
            ORDER BY bt.total_amount DESC
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"date": date, "limit": limit})
        return [row._mapping for row in result.fetchall()]

    async def get_lhb(self, date: str | None, limit: int = 50) -> list[dict]:
        """获取龙虎榜数据"""
        date = await self._resolve_trade_date(date, "stock_tops")
        if not date:
            return []

        query = text("""
            SELECT
                split_part(t.ts_code, '.', 1) as code,
                COALESCE(s.name, '') as name,
                db.close as close,
                db.pct_chg as change_rate,
                t.net_amount as net_amount,
                t.sum_buy as buy_amount,
                t.sum_sell as sell_amount,
                t.ranking_times,
                t.trade_date
            FROM stock_tops t
            LEFT JOIN stocks s ON split_part(t.ts_code, '.', 1) = s.symbol
            LEFT JOIN daily_bars db ON s.ts_code = db.ts_code AND db.trade_date = t.trade_date
            WHERE t.trade_date = :date
            ORDER BY t.net_amount DESC NULLS LAST
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"date": date, "limit": limit})
        return [row._mapping for row in result.fetchall()]

    async def get_north_bound_funds(self, date: str | None, limit: int = 50) -> list[dict]:
        """获取北向资金数据"""
        date = await self._resolve_trade_date(date, "north_bound_funds")
        if not date:
            return []

        query = text("""
            SELECT
                split_part(nb.ts_code, '.', 1) as code,
                COALESCE(s.name, '') as name,
                nb.close as close,
                nb.pct_chg as change_rate,
                nb.sh_net_inflow,
                nb.sz_net_inflow,
                nb.total_net_inflow,
                nb.trade_date
            FROM north_bound_funds nb
            LEFT JOIN stocks s ON split_part(nb.ts_code, '.', 1) = s.symbol
            WHERE nb.trade_date = :date
            ORDER BY nb.total_net_inflow DESC NULLS LAST
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"date": date, "limit": limit})
        return [row._mapping for row in result.fetchall()]
