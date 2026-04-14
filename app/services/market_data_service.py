from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.date_utils import trade_date_dt_param


class MarketDataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def _resolve_trade_date(
        self, target_date: str | None, table_name: str = "daily_bars"
    ) -> str | None:
        core_fact_tables = {"daily_bars", "fund_flows"}
        if table_name not in {
            "daily_bars",
            "fund_flows",
            "stock_block_trades",
            "stock_tops",
            "north_bound_funds",
        }:
            raise ValueError(f"unsupported trade date table: {table_name}")
        if target_date:
            target_date_dt = trade_date_dt_param(target_date)
            date_predicate = (
                "(trade_date_dt <= :target_date_dt OR (trade_date_dt IS NULL AND trade_date <= :target_date))"
                if table_name in core_fact_tables
                else "trade_date <= :target_date"
            )
            result = await self.db.execute(
                text(f"""
                    SELECT MAX(trade_date) as resolved_date
                    FROM {table_name}
                    WHERE {date_predicate}
                    """),
                {"target_date": target_date, "target_date_dt": target_date_dt},
            )
        else:
            order_column = "trade_date_dt" if table_name in core_fact_tables else "trade_date"
            result = await self.db.execute(
                text(f"""
                    SELECT trade_date as resolved_date
                    FROM {table_name}
                    ORDER BY
                        CASE WHEN {order_column} IS NULL THEN 1 ELSE 0 END,
                        {order_column} DESC,
                        trade_date DESC
                    LIMIT 1
                    """)
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def get_fund_flow_rank(self, date: str | None, limit: int = 50) -> list[dict]:
        """获取资金流排行"""
        date = await self._resolve_trade_date(date, "fund_flows")
        if not date:
            return []
        date_dt = trade_date_dt_param(date)

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
            INNER JOIN daily_bars db ON s.ts_code = db.ts_code
              AND (
                db.trade_date_dt = f.trade_date_dt
                OR (db.trade_date_dt IS NULL AND f.trade_date_dt IS NULL AND db.trade_date = f.trade_date)
              )
            WHERE f.trade_date_dt = :date_dt
               OR (f.trade_date_dt IS NULL AND f.trade_date = :date)
            ORDER BY f.net_amount_main DESC NULLS LAST
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"date": date, "date_dt": date_dt, "limit": limit})
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
        date_dt = trade_date_dt_param(date)

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
            LEFT JOIN daily_bars db
                ON s.ts_code = db.ts_code
                AND (db.trade_date_dt = :date_dt OR (db.trade_date_dt IS NULL AND db.trade_date = :date))
            WHERE t.trade_date = :date
            ORDER BY t.net_amount DESC NULLS LAST
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"date": date, "date_dt": date_dt, "limit": limit})
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

    async def get_task_health(self, alert_limit: int = 10) -> dict:
        """返回关键抓取任务的用户可见健康摘要。"""
        baseline_trade_date = await self._resolve_trade_date(None, "daily_bars")
        datasets: list[dict] = []
        for dataset in ("daily_bars", "fund_flows", "stock_tops", "stock_block_trades"):
            latest_trade_date = await self._resolve_trade_date(None, dataset)
            datasets.append(
                {
                    "dataset": dataset,
                    "latest_trade_date": latest_trade_date,
                    "baseline_trade_date": baseline_trade_date,
                    "current": bool(
                        latest_trade_date
                        and baseline_trade_date
                        and latest_trade_date == baseline_trade_date
                    ),
                }
            )

        latest_alerts_query = text("""
            WITH latest_status AS (
                SELECT
                    task_name,
                    entity_type,
                    entity_key,
                    MAX(updated_at) AS latest_updated_at
                FROM data_fetch_audit
                WHERE entity_type IS NOT NULL AND entity_key IS NOT NULL
                GROUP BY task_name, entity_type, entity_key
            )
            SELECT
                audit.task_name,
                audit.entity_type,
                audit.entity_key,
                audit.trade_date,
                audit.status,
                audit.source,
                audit.note,
                audit.updated_at
            FROM data_fetch_audit AS audit
            INNER JOIN latest_status AS latest
                ON audit.task_name = latest.task_name
                AND audit.entity_type = latest.entity_type
                AND audit.entity_key = latest.entity_key
                AND audit.updated_at = latest.latest_updated_at
            WHERE audit.status <> 'done'
                AND audit.entity_type IS NOT NULL
                AND audit.entity_key IS NOT NULL
            ORDER BY audit.updated_at DESC, audit.task_name ASC
            LIMIT :limit
        """)
        alert_count_query = text("""
            WITH latest_status AS (
                SELECT
                    task_name,
                    entity_type,
                    entity_key,
                    MAX(updated_at) AS latest_updated_at
                FROM data_fetch_audit
                WHERE entity_type IS NOT NULL AND entity_key IS NOT NULL
                GROUP BY task_name, entity_type, entity_key
            )
            SELECT COUNT(*)
            FROM data_fetch_audit AS audit
            INNER JOIN latest_status AS latest
                ON audit.task_name = latest.task_name
                AND audit.entity_type = latest.entity_type
                AND audit.entity_key = latest.entity_key
                AND audit.updated_at = latest.latest_updated_at
            WHERE audit.status <> 'done'
                AND audit.entity_type IS NOT NULL
                AND audit.entity_key IS NOT NULL
        """)

        try:
            alerts_result = await self.db.execute(latest_alerts_query, {"limit": alert_limit})
            alert_count_result = await self.db.execute(alert_count_query)
            alerts = [dict(row._mapping) for row in alerts_result.fetchall()]
            alert_count = int(alert_count_result.scalar() or 0)
        except SQLAlchemyError:
            alerts = []
            alert_count = 0

        return {
            "baseline_trade_date": baseline_trade_date,
            "datasets": datasets,
            "alerts": alerts,
            "alert_count": alert_count,
        }

    async def get_summary(self) -> dict:
        """返回首页市场温度计所需的聚合摘要。"""
        trade_date = await self._resolve_trade_date(None, "daily_bars")
        if not trade_date:
            return {
                "trade_date": None,
                "total_count": 0,
                "up_count": 0,
                "down_count": 0,
                "flat_count": 0,
                "limit_up_count": 0,
                "limit_down_count": 0,
                "sentiment_summary": "当前没有可用的盘后行情数据。",
                "indices": [],
            }

        query = text("""
            SELECT
                s.symbol,
                s.name,
                s.market,
                s.exchange,
                s.is_etf,
                db.close,
                db.pct_chg,
                db.trade_date
            FROM daily_bars db
            INNER JOIN stocks s ON s.ts_code = db.ts_code
            WHERE (
                db.trade_date_dt = :trade_date_dt
                OR (db.trade_date_dt IS NULL AND db.trade_date = :trade_date)
              )
              AND COALESCE(s.list_status, 'L') = 'L'
              AND COALESCE(s.is_etf, false) = false
            ORDER BY s.symbol ASC
        """)
        result = await self.db.execute(
            query, {"trade_date": trade_date, "trade_date_dt": trade_date_dt_param(trade_date)}
        )
        rows = [dict(row._mapping) for row in result.fetchall()]

        if not rows:
            return {
                "trade_date": trade_date,
                "total_count": 0,
                "up_count": 0,
                "down_count": 0,
                "flat_count": 0,
                "limit_up_count": 0,
                "limit_down_count": 0,
                "sentiment_summary": "当前交易日没有可用于首页聚合的股票行情。",
                "indices": self._build_index_placeholders(trade_date, "暂无可用成分数据"),
            }

        up_count = 0
        down_count = 0
        flat_count = 0
        limit_up_count = 0
        limit_down_count = 0
        total_change = 0.0
        total_change_weight = 0
        index_buckets: dict[str, list[dict]] = {
            "sh_index": [],
            "sz_index": [],
            "chinext_index": [],
        }

        for row in rows:
            pct_chg = self._to_float(row.get("pct_chg"))
            if pct_chg is None:
                continue

            total_change += pct_chg
            total_change_weight += 1

            if abs(pct_chg) < 0.005:
                flat_count += 1
            elif pct_chg > 0:
                up_count += 1
            else:
                down_count += 1

            threshold = self._limit_threshold(row)
            if pct_chg >= threshold:
                limit_up_count += 1
            elif pct_chg <= -threshold:
                limit_down_count += 1

            bucket = self._market_bucket(row)
            if bucket in index_buckets:
                index_buckets[bucket].append(row)

        indices = [
            self._build_index_summary(
                code="sh_index",
                name="上证综指代理",
                rows=index_buckets["sh_index"],
                trade_date=trade_date,
                note="基于上海市场股票日涨跌幅的代理摘要",
            ),
            self._build_index_summary(
                code="sz_index",
                name="深成综指代理",
                rows=index_buckets["sz_index"],
                trade_date=trade_date,
                note="基于深圳市场股票日涨跌幅的代理摘要",
            ),
            self._build_index_summary(
                code="chinext_index",
                name="创业板代理",
                rows=index_buckets["chinext_index"],
                trade_date=trade_date,
                note="基于创业板股票日涨跌幅的代理摘要",
            ),
        ]

        avg_change = total_change / total_change_weight if total_change_weight else 0.0
        sentiment_summary = self._build_sentiment_summary(
            trade_date=trade_date,
            total_count=total_change_weight,
            up_count=up_count,
            down_count=down_count,
            flat_count=flat_count,
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
            avg_change=avg_change,
            indices=indices,
        )

        return {
            "trade_date": trade_date,
            "total_count": total_change_weight,
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "sentiment_summary": sentiment_summary,
            "indices": indices,
        }

    @staticmethod
    def _market_bucket(row: dict) -> str | None:
        symbol = str(row.get("symbol") or "")
        market = str(row.get("market") or "")
        exchange = str(row.get("exchange") or "")

        if symbol.startswith("3") or market == "创业板":
            return "chinext_index"
        if symbol.startswith("688") or market == "科创板":
            return "sh_index"
        if symbol.startswith("0") or symbol.startswith("2") or exchange.upper() in {"SZSE", "SZ"}:
            return "sz_index"
        if symbol.startswith("6") or exchange.upper() in {"SSE", "SH"}:
            return "sh_index"
        return None

    @staticmethod
    def _limit_threshold(row: dict) -> float:
        symbol = str(row.get("symbol") or "")
        market = str(row.get("market") or "")
        if symbol.startswith("3") or symbol.startswith("688") or market in {"创业板", "科创板"}:
            return 19.5
        return 9.5

    def _build_index_placeholders(self, trade_date: str | None, note: str) -> list[dict]:
        return [
            {
                "code": "sh_index",
                "name": "上证综指代理",
                "trade_date": trade_date,
                "current": None,
                "change": None,
                "change_rate": None,
                "constituent_count": 0,
                "source": "fallback",
                "note": note,
            },
            {
                "code": "sz_index",
                "name": "深成综指代理",
                "trade_date": trade_date,
                "current": None,
                "change": None,
                "change_rate": None,
                "constituent_count": 0,
                "source": "fallback",
                "note": note,
            },
            {
                "code": "chinext_index",
                "name": "创业板代理",
                "trade_date": trade_date,
                "current": None,
                "change": None,
                "change_rate": None,
                "constituent_count": 0,
                "source": "fallback",
                "note": note,
            },
        ]

    def _build_index_summary(
        self,
        *,
        code: str,
        name: str,
        rows: list[dict],
        trade_date: str | None,
        note: str | None = None,
    ) -> dict:
        if not rows:
            return {
                "code": code,
                "name": name,
                "trade_date": trade_date,
                "current": None,
                "change": None,
                "change_rate": None,
                "constituent_count": 0,
                "source": "fallback",
                "note": note or "暂无可用成分数据",
            }

        change_rates = [self._to_float(row.get("pct_chg")) for row in rows]
        change_rates = [value for value in change_rates if value is not None]
        avg_change_rate = sum(change_rates) / len(change_rates) if change_rates else None

        return {
            "code": code,
            "name": name,
            "trade_date": trade_date,
            "current": None,
            "change": None,
            "change_rate": round(avg_change_rate, 4) if avg_change_rate is not None else None,
            "constituent_count": len(rows),
            "source": "proxy",
            "note": note,
        }

    def _build_sentiment_summary(
        self,
        *,
        trade_date: str,
        total_count: int,
        up_count: int,
        down_count: int,
        flat_count: int,
        limit_up_count: int,
        limit_down_count: int,
        avg_change: float,
        indices: list[dict],
    ) -> str:
        if total_count <= 0:
            return "当前没有可用的盘后行情数据。"

        up_ratio = up_count / total_count if total_count else 0
        down_ratio = down_count / total_count if total_count else 0
        bullish_indices = sum(1 for item in indices if (item.get("change_rate") or 0) > 0)
        bearish_indices = sum(1 for item in indices if (item.get("change_rate") or 0) < 0)

        if up_ratio >= 0.6 and limit_up_count >= limit_down_count and avg_change > 0:
            mood = "市场偏强，涨多跌少，情绪积极。"
        elif down_ratio >= 0.6 and limit_down_count >= limit_up_count and avg_change < 0:
            mood = "市场偏弱，跌多涨少，情绪偏谨慎。"
        elif bullish_indices > bearish_indices:
            mood = "主要指数多数收涨，整体情绪略偏多。"
        elif bearish_indices > bullish_indices:
            mood = "主要指数多数收跌，整体情绪略偏空。"
        else:
            mood = "市场分歧较大，整体情绪中性。"

        return (
            f"{trade_date} 收盘：上涨 {up_count} 只、下跌 {down_count} 只、平盘 {flat_count} 只，"
            f"涨停 {limit_up_count} 只、跌停 {limit_down_count} 只。{mood}"
        )
