from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.providers.market_data_provider import MarketDataProvider


class SelectionService:
    """Unified selection service with optional provider support.

    If provider is supplied, screening uses MarketDataProvider;
    otherwise falls back to direct SQL queries.
    """

    def __init__(self, db: AsyncSession | None = None, provider: MarketDataProvider | None = None):
        self.db = db
        self.provider = provider

    @staticmethod
    def get_conditions() -> dict[str, Any]:
        return {
            "markets": ["沪市", "深市", "创业板", "科创板"],
            "indicators": ["macd", "kdj", "boll", "rsi"],
            "strategies": ["放量上涨", "均线多头", "停机坪"],
        }

    @classmethod
    def get_screening_metadata(cls) -> dict[str, Any]:
        payload = cls.get_conditions()
        payload["filter_fields"] = [
            {
                "key": "priceMin",
                "label": "最低价格",
                "value_type": "number",
                "operators": [">="],
            },
            {
                "key": "priceMax",
                "label": "最高价格",
                "value_type": "number",
                "operators": ["<="],
            },
            {
                "key": "changeMin",
                "label": "最小涨跌幅",
                "value_type": "number",
                "operators": [">="],
            },
            {
                "key": "changeMax",
                "label": "最大涨跌幅",
                "value_type": "number",
                "operators": ["<="],
            },
            {
                "key": "market",
                "label": "市场范围",
                "value_type": "enum",
                "operators": ["="],
            },
            # Technical indicators
            {
                "key": "rsiMin",
                "label": "RSI 下限",
                "value_type": "number",
                "operators": [">="],
                "description": "RSI 指标最小值 (0-100)",
            },
            {
                "key": "rsiMax",
                "label": "RSI 上限",
                "value_type": "number",
                "operators": ["<="],
                "description": "RSI 指标最大值 (0-100)",
            },
            {
                "key": "macdBullish",
                "label": "MACD 看涨",
                "value_type": "boolean",
                "operators": ["="],
                "description": "是否要求 MACD 金叉/柱状图为正",
            },
            {
                "key": "macdBearish",
                "label": "MACD 看跌",
                "value_type": "boolean",
                "operators": ["="],
                "description": "是否要求 MACD 死叉/柱状图为负",
            },
            # Patterns (coming soon)
            {
                "key": "pattern",
                "label": "形态筛选",
                "value_type": "enum",
                "operators": ["="],
                "description": "形态类型（即将推出）",
                "coming_soon": True,
            },
        ]
        return payload

    @staticmethod
    def get_templates() -> list[dict[str, Any]]:
        """Return predefined screening condition templates."""
        return [
            {
                "id": "low-psi-oversold",
                "name": "低位反弹",
                "description": "价格低位 + RSI 超卖 + MACD 转多头",
                "icon": "📈",
                "filters": {
                    "priceMin": 2.0,
                    "priceMax": 15.0,
                    "rsiMin": 0,
                    "rsiMax": 30,
                    "macdBullish": True,
                },
            },
            {
                "id": "strong-breakout",
                "name": "强势突破",
                "description": "价格突破 + 量增 + RSI 强势",
                "icon": "🚀",
                "filters": {
                    "priceMin": 5.0,
                    "changeMin": 5.0,
                    "rsiMin": 50,
                    "rsiMax": 80,
                },
            },
            {
                "id": "high-quality-blue",
                "name": "优质蓝筹",
                "description": "低估值 + 价格稳定 + 市场龙头",
                "icon": "🏦",
                "filters": {
                    "priceMin": 5.0,
                    "priceMax": 20.0,
                    "changeMin": -2.0,
                    "changeMax": 3.0,
                },
            },
            {
                "id": "speculative-momentum",
                "name": "题材 momentum",
                "description": "中小盘 + 活跃 + 涨跌波动大",
                "icon": "🔥",
                "filters": {
                    "priceMin": 3.0,
                    "priceMax": 30.0,
                    "changeMin": -5.0,
                    "changeMax": 10.0,
                },
            },
            {
                "id": "macd-golden-cross",
                "name": "MACD 金叉池",
                "description": "仅筛选 MACD 看涨信号",
                "icon": "✨",
                "filters": {
                    "macdBullish": True,
                },
            },
            {
                "id": "rsi-neutral",
                "name": "RSI 中性区间",
                "description": "排除超买超卖，寻找正常波动股",
                "icon": "🎯",
                "filters": {
                    "rsiMin": 30,
                    "rsiMax": 70,
                },
            },
        ]

    async def _resolve_trade_date(self, date: str | None) -> str | None:
        if not self.db:
            return None
        if date:
            result = await self.db.execute(
                text("""
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date <= :target_date
                    """),
                {"target_date": date},
            )
        else:
            result = await self.db.execute(
                text("SELECT MAX(trade_date) AS resolved_date FROM daily_bars")
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    @staticmethod
    def _format_condition_value(key: str, value: Any) -> str | int | float | bool:
        if key in {"priceMin", "priceMax", "changeMin", "changeMax"}:
            return round(float(value), 4)
        if key in {"rsiMin", "rsiMax"}:
            return round(float(value), 1)
        return value

    @staticmethod
    def _build_condition_evidence(
        *,
        key: str,
        label: str,
        operator: str,
        condition: Any,
        actual_value: Any,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "value": round(float(actual_value), 4)
            if isinstance(actual_value, (int, float))
            else actual_value,
            "operator": operator,
            "condition": SelectionService._format_condition_value(key, condition),
            "matched": True,
        }

    def _build_reason(self, conditions: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
        pct = float(row["pct_chg"] or 0)
        amount = float(row["amount"] or 0)
        close = float(row["close"] or 0)
        market_value = "sh" if str(row["ts_code"]).endswith(".SH") else "sz"
        evidence: list[dict[str, Any]] = []
        summary_parts: list[str] = []

        # Basic price and change conditions
        if conditions.get("priceMin") is not None:
            value = float(conditions["priceMin"])
            summary_parts.append(f"Close >= {value:.2f}")
            evidence.append(
                self._build_condition_evidence(
                    key="close",
                    label="Close",
                    operator=">=",
                    condition=value,
                    actual_value=close,
                )
            )
        if conditions.get("priceMax") is not None:
            value = float(conditions["priceMax"])
            summary_parts.append(f"Close <= {value:.2f}")
            evidence.append(
                self._build_condition_evidence(
                    key="close",
                    label="Close",
                    operator="<=",
                    condition=value,
                    actual_value=close,
                )
            )
        if conditions.get("changeMin") is not None:
            value = float(conditions["changeMin"])
            summary_parts.append(f"Change >= {value:.2f}%")
            evidence.append(
                self._build_condition_evidence(
                    key="change_rate",
                    label="Daily change",
                    operator=">=",
                    condition=value,
                    actual_value=pct,
                )
            )
        if conditions.get("changeMax") is not None:
            value = float(conditions["changeMax"])
            summary_parts.append(f"Change <= {value:.2f}%")
            evidence.append(
                self._build_condition_evidence(
                    key="change_rate",
                    label="Daily change",
                    operator="<=",
                    condition=value,
                    actual_value=pct,
                )
            )
        if conditions.get("market"):
            summary_parts.append(f"Market = {conditions['market']}")
            evidence.append(
                {
                    "key": "market",
                    "label": "Market",
                    "value": market_value,
                    "operator": "=",
                    "condition": str(conditions["market"]),
                    "matched": market_value == str(conditions["market"]),
                }
            )

        # RSI conditions
        rsi_value = row.get("rsi")
        if rsi_value is not None:
            rsi = float(rsi_value)
            if conditions.get("rsiMin") is not None:
                value = float(conditions["rsiMin"])
                matched = rsi >= value
                evidence.append(
                    self._build_condition_evidence(
                        key="rsi",
                        label="RSI",
                        operator=">=",
                        condition=value,
                        actual_value=rsi,
                    )
                )
                if matched:
                    summary_parts.append(f"RSI >= {value:.0f}")
            if conditions.get("rsiMax") is not None:
                value = float(conditions["rsiMax"])
                matched = rsi <= value
                evidence.append(
                    self._build_condition_evidence(
                        key="rsi",
                        label="RSI",
                        operator="<=",
                        condition=value,
                        actual_value=rsi,
                    )
                )
                if matched:
                    summary_parts.append(f"RSI <= {value:.0f}")

        # MACD conditions
        macd_value = row.get("macd")
        macd_signal = row.get("macd_signal")
        if macd_value is not None and conditions.get("macdBullish"):
            # Bullish: MACD > signal (golden cross tendency)
            matched = macd_value > macd_signal if macd_signal is not None else False
            evidence.append(
                {
                    "key": "macd",
                    "label": "MACD",
                    "value": round(float(macd_value), 4),
                    "operator": "> signal (bullish)",
                    "condition": True,
                    "matched": matched,
                }
            )
            if matched:
                summary_parts.append("MACD bullish")
        if macd_value is not None and conditions.get("macdBearish"):
            # Bearish: MACD < signal (dead cross tendency)
            matched = macd_value < macd_signal if macd_signal is not None else False
            evidence.append(
                {
                    "key": "macd",
                    "label": "MACD",
                    "value": round(float(macd_value), 4),
                    "operator": "< signal (bearish)",
                    "condition": True,
                    "matched": matched,
                }
            )
            if matched:
                summary_parts.append("MACD bearish")

        if summary_parts:
            summary = "; ".join(summary_parts[:3])
        else:
            summary = f"Included in latest screening universe with daily change {pct:.2f}%"
            evidence = [
                {
                    "key": "close",
                    "label": "Close",
                    "value": round(close, 4),
                    "matched": True,
                },
                {
                    "key": "change_rate",
                    "label": "Daily change",
                    "value": round(pct, 4),
                    "matched": True,
                },
                {
                    "key": "amount",
                    "label": "Turnover",
                    "value": round(amount, 4),
                    "matched": True,
                },
            ]

        return {"summary": summary, "evidence": evidence}

    async def run_selection(
        self, conditions: dict[str, Any], date: str | None, limit: int = 300
    ) -> list[dict]:
        # If provider is available, delegate to provider-based implementation
        if self.provider:
            try:
                results = await self._run_selection_with_provider(conditions, date, limit)
                if results:
                    return results
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Provider-based selection failed, falling back to SQL: %s", exc
                )

        # SQL-based implementation (default fallback)
        return await self._run_selection_with_sql(conditions, date, limit)

    async def _run_selection_with_sql(
        self, conditions: dict[str, Any], date: str | None, limit: int = 300
    ) -> list[dict]:
        """Execute screening using direct SQL queries."""

        trade_date = await self._resolve_trade_date(date)
        if not trade_date:
            return []

        price_min = conditions.get("priceMin")
        price_max = conditions.get("priceMax")
        change_min = conditions.get("changeMin")
        change_max = conditions.get("changeMax")
        market = conditions.get("market")
        rsi_min = conditions.get("rsiMin")
        rsi_max = conditions.get("rsiMax")
        macd_bullish = conditions.get("macdBullish")
        macd_bearish = conditions.get("macdBearish")

        where_sql = [
            "s.list_status = 'L'",
            "s.is_etf = false",
            "db.trade_date = :trade_date",
        ]
        params: dict[str, Any] = {"trade_date": trade_date}

        if price_min is not None:
            where_sql.append("db.close >= :price_min")
            params["price_min"] = price_min
        if price_max is not None:
            where_sql.append("db.close <= :price_max")
            params["price_max"] = price_max
        if change_min is not None:
            where_sql.append("db.pct_chg >= :change_min")
            params["change_min"] = change_min
        if change_max is not None:
            where_sql.append("db.pct_chg <= :change_max")
            params["change_max"] = change_max
        if market == "sh":
            where_sql.append("s.symbol LIKE '6%'")
        elif market == "sz":
            where_sql.append("(s.symbol LIKE '0%' OR s.symbol LIKE '3%')")

        # Build base query with optional indicator joins
        select_fields = """
            s.ts_code,
            s.symbol AS code,
            s.name AS stock_name,
            db.trade_date,
            db.close,
            db.pct_chg,
            db.vol,
            db.amount
        """

        from_clause = """
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            WHERE {where_clause}
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :limit
        """.format(
            where_clause=" AND ".join(where_sql)
        )

        # If indicator filters are active, we need to join indicators table
        if rsi_min is not None or rsi_max is not None or macd_bullish or macd_bearish:
            # Add indicator joins using conditional aggregation or subqueries
            select_fields += """,
            COALESCE(MAX(CASE WHEN i.indicator_name = 'RSI' THEN i.indicator_value END), 0) AS rsi,
            COALESCE(MAX(CASE WHEN i.indicator_name = 'MACD' THEN i.indicator_value END), 0) AS macd,
            COALESCE(MAX(CASE WHEN i.indicator_name = 'MACD_SIGNAL' THEN i.indicator_value END), 0) AS macd_signal
            """
            from_clause = """
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            LEFT JOIN indicators i ON s.ts_code = i.ts_code AND i.trade_date = db.trade_date
            WHERE {where_clause}
            GROUP BY s.ts_code, s.symbol, s.name, db.trade_date, db.close, db.pct_chg, db.vol, db.amount
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :limit
            """.format(
                where_clause=" AND ".join(where_sql)
            )
        else:
            from_clause = """
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            WHERE {where_clause}
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :limit
            """.format(
                where_clause=" AND ".join(where_sql)
            )

        sql = text(f"SELECT{select_fields}{from_clause}")
        params["limit"] = limit
        rows = (await self.db.execute(sql, params)).mappings().all()

        # Apply indicator filters that couldn't be done in SQL
        filtered_rows = []
        for row in rows:
            include = True
            if rsi_min is not None:
                rsi = float(row.get("rsi") or 0)
                if rsi < rsi_min:
                    include = False
            if rsi_max is not None and include:
                rsi = float(row.get("rsi") or 0)
                if rsi > rsi_max:
                    include = False
            if macd_bullish and include:
                macd = float(row.get("macd") or 0)
                macd_sig = float(row.get("macd_signal") or 0)
                if macd <= macd_sig:
                    include = False
            if macd_bearish and include:
                macd = float(row.get("macd") or 0)
                macd_sig = float(row.get("macd_signal") or 0)
                if macd >= macd_sig:
                    include = False
            if include:
                filtered_rows.append(row)

        # Limit after filtering
        rows = filtered_rows[:limit]

        results: list[dict] = []
        for row in rows:
            pct = float(row["pct_chg"] or 0)
            amt = float(row["amount"] or 0)
            score = pct * 5 + min(amt / 1e8, 20)
            signal = "hold"
            if pct >= 2:
                signal = "buy"
            elif pct <= -2:
                signal = "sell"
            reason = self._build_reason(conditions, dict(row))
            results.append(
                {
                    "ts_code": row["ts_code"],
                    "code": row["code"],
                    "stock_name": row["stock_name"],
                    "score": round(score, 4),
                    "signal": signal,
                    "trade_date": row["trade_date"],
                    "date": row["trade_date"],
                    "close": float(row["close"] or 0),
                    "change_rate": pct,
                    "amount": amt,
                    "reason_summary": reason["summary"],
                    "evidence": reason["evidence"],
                    "reason": reason,
                }
            )
        return results

    async def get_history(self, date: str | None, limit: int) -> list[dict]:
        if not self.db:
            return []
        where = []
        params: dict[str, Any] = {"limit": limit}
        if date:
            where.append("sr.trade_date = :trade_date")
            params["trade_date"] = date
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = text(f"""
            SELECT
                sr.selection_id,
                sr.ts_code,
                split_part(sr.ts_code, '.', 1) AS code,
                s.name AS stock_name,
                sr.trade_date,
                sr.score
            FROM selection_results sr
            LEFT JOIN stocks s ON s.ts_code = sr.ts_code
            {where_sql}
            ORDER BY sr.trade_date DESC
            LIMIT :limit
            """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        return [
            {
                "selection_id": row["selection_id"],
                "ts_code": row["ts_code"],
                "code": row["code"],
                "stock_name": row["stock_name"],
                "trade_date": row["trade_date"],
                "date": row["trade_date"],
                "score": float(row["score"] or 0),
                "signal": "hold",
                "reason_summary": f"Historical screening record {row['selection_id']}",
            }
            for row in rows
        ]

    async def compare_results(self, history_ids: list[str]) -> list[dict[str, Any]]:
        """Compare multiple screening result sets by selection_id."""
        if not self.db or not history_ids:
            return []

        # Fetch aggregated data for each selection_id
        sql = text("""
            SELECT
                sr.selection_id,
                COUNT(*) AS total,
                AVG(sr.score) AS avg_score,
                MAX(sr.trade_date) AS trade_date
            FROM selection_results sr
            WHERE sr.selection_id = ANY(:ids)
            GROUP BY sr.selection_id
        """)
        result = await self.db.execute(sql, {"ids": history_ids})
        aggregates = {row["selection_id"]: dict(row) for row in result.mappings().all()}

        # Fetch top stocks for each selection_id (top 5 by score)
        sql_top = text("""
            SELECT
                sr.selection_id,
                sr.ts_code,
                split_part(sr.ts_code, '.', 1) AS code,
                s.name AS stock_name,
                sr.trade_date,
                sr.score
            FROM selection_results sr
            LEFT JOIN stocks s ON s.ts_code = sr.ts_code
            WHERE sr.selection_id = ANY(:ids)
            AND sr.score IS NOT NULL
            ORDER BY sr.selection_id, sr.score DESC
        """)
        top_rows = (await self.db.execute(sql_top, {"ids": history_ids})).mappings().all()

        # Organize top stocks by selection_id
        top_by_selection: dict[str, list[dict[str, Any]]] = {}
        for row in top_rows:
            sel_id = row["selection_id"]
            if sel_id not in top_by_selection:
                top_by_selection[sel_id] = []
            if len(top_by_selection[sel_id]) < 5:
                top_by_selection[sel_id].append({
                    "selection_id": sel_id,
                    "ts_code": row["ts_code"],
                    "code": row["code"],
                    "stock_name": row["stock_name"],
                    "trade_date": row["trade_date"],
                    "date": row["trade_date"],
                    "score": float(row["score"] or 0),
                    "signal": "hold",
                    "reason_summary": None,
                })

        # Build response items
        comparison_items: list[dict[str, Any]] = []
        for sel_id in history_ids:
            agg = aggregates.get(sel_id)
            if not agg:
                continue
            comparison_items.append({
                "history_id": sel_id,
                "trade_date": agg["trade_date"],
                "total": int(agg["total"]),
                "avg_score": round(float(agg["avg_score"] or 0), 4),
                "top_stocks": top_by_selection.get(sel_id, []),
            })

        return comparison_items

    async def _run_selection_with_provider(
        self, conditions: dict[str, Any], date: str | None, limit: int = 300
    ) -> list[dict]:
        """Execute screening using MarketDataProvider.

        Falls back to SQL if provider is not available or returns empty.
        """
        if not self.provider:
            return []

        import logging
        import pandas as pd
        from datetime import date as date_cls

        logger = logging.getLogger(__name__)

        price_min = conditions.get("priceMin")
        price_max = conditions.get("priceMax")
        change_min = conditions.get("changeMin")
        change_max = conditions.get("changeMax")
        market = conditions.get("market")
        rsi_min = conditions.get("rsiMin")
        rsi_max = conditions.get("rsiMax")
        macd_bullish = conditions.get("macdBullish", False)
        macd_bearish = conditions.get("macdBearish", False)

        # Resolve target date
        if date:
            target_date = date_cls.fromisoformat(date)
        else:
            target_date = await self.provider.get_latest_trade_date()

        # Get stock list (with market filter)
        markets_map = {
            "sh": ["沪市"],
            "sz": ["深市"],
            "创业板": ["创业板"],
            "科创板": ["科创板"],
        }
        market_filters = markets_map.get(market) if market else None
        stock_list_df = await self.provider.get_stock_list(
            markets=market_filters,
            active_only=True,
        )
        if stock_list_df.empty:
            return []

        codes = stock_list_df["code"].tolist()

        # Get daily bars
        bars_df = await self.provider.get_daily_bars(
            codes=codes,
            start_date=target_date,
            end_date=target_date,
            adjusted=True,
        )
        if bars_df.empty:
            return []

        # Apply price/change filters
        filtered = bars_df.copy()
        if price_min is not None:
            filtered = filtered[filtered["close"] >= price_min]
        if price_max is not None:
            filtered = filtered[filtered["close"] <= price_max]
        if change_min is not None:
            filtered = filtered[filtered["pct_chg"] >= change_min]
        if change_max is not None:
            filtered = filtered[filtered["pct_chg"] <= change_max]

        if filtered.empty:
            return []

        # If no indicator filters needed, return basic results
        if not (rsi_min or rsi_max or macd_bullish or macd_bearish):
            return self._format_provider_results(filtered, conditions, target_date, limit)

        # Get technical indicators for filtered stocks
        try:
            final_codes = filtered["code"].unique().tolist()
            technicals_df = await self.provider.get_technicals(
                code=None,
                indicators=["rsi", "macd", "macd_signal"],
                start_date=target_date,
                end_date=target_date,
            )
            if not technicals_df.empty:
                # Merge and filter by indicators
                merged = filtered.merge(
                    technicals_df[["code", "rsi", "macd", "macd_signal"]],
                    on="code",
                    how="left",
                )
                if rsi_min is not None:
                    merged = merged[(merged["rsi"].notna()) & (merged["rsi"] >= rsi_min)]
                if rsi_max is not None:
                    merged = merged[(merged["rsi"].notna()) & (merged["rsi"] <= rsi_max)]
                if macd_bullish:
                    merged = merged[
                        (merged["macd"].notna())
                        & (merged["macd_signal"].notna())
                        & (merged["macd"] > merged["macd_signal"])
                    ]
                if macd_bearish:
                    merged = merged[
                        (merged["macd"].notna())
                        & (merged["macd_signal"].notna())
                        & (merged["macd"] < merged["macd_signal"])
                    ]
                return self._format_provider_results(merged, conditions, target_date, limit)
        except Exception as exc:
            logger.warning("Indicator fetch via provider failed: %s", exc)

        return self._format_provider_results(filtered, conditions, target_date, limit)

    def _format_provider_results(
        self, df, conditions: dict[str, Any], trade_date, limit: int
    ) -> list[dict]:
        """Format provider DataFrame results into standard screening output."""
        results = []
        for _, row in df.head(limit).iterrows():
            pct = float(row.get("pct_chg", 0))
            close = float(row.get("close", 0))
            amount = float(row.get("amount", 0))
            ts_code = str(row.get("ts_code", row.get("code", "")))
            code = str(row.get("code", ts_code.split(".")[0]))
            stock_name = str(row.get("stock_name", row.get("name", "")))
            date_str = str(trade_date).replace("-", "")

            # Build evidence
            evidence = []
            if conditions.get("priceMin") is not None:
                evidence.append({
                    "key": "close", "label": "Close",
                    "value": close, "operator": ">=",
                    "condition": float(conditions["priceMin"]),
                    "matched": close >= float(conditions["priceMin"]),
                })
            if conditions.get("priceMax") is not None:
                evidence.append({
                    "key": "close", "label": "Close",
                    "value": close, "operator": "<=",
                    "condition": float(conditions["priceMax"]),
                    "matched": close <= float(conditions["priceMax"]),
                })
            if conditions.get("changeMin") is not None:
                evidence.append({
                    "key": "change_rate", "label": "Daily change",
                    "value": round(pct, 4), "operator": ">=",
                    "condition": float(conditions["changeMin"]),
                    "matched": pct >= float(conditions["changeMin"]),
                })
            if conditions.get("changeMax") is not None:
                evidence.append({
                    "key": "change_rate", "label": "Daily change",
                    "value": round(pct, 4), "operator": "<=",
                    "condition": float(conditions["changeMax"]),
                    "matched": pct <= float(conditions["changeMax"]),
                })

            if evidence:
                summary = "; ".join(
                    f"{e['label']} {e['operator']} {e['condition']}" for e in evidence
                )
            else:
                summary = f"Included in screening (pct_chg={pct:.2f}%)"

            score = round(pct * 5 + min(amount / 1e8, 20), 4)
            signal = "buy" if pct >= 2 else ("sell" if pct <= -2 else "hold")

            results.append({
                "ts_code": ts_code,
                "code": code,
                "stock_name": stock_name,
                "score": score,
                "signal": signal,
                "trade_date": date_str,
                "date": date_str,
                "close": close,
                "change_rate": pct,
                "amount": amount,
                "reason_summary": summary,
                "evidence": evidence,
                "reason": {"summary": summary, "evidence": evidence},
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
