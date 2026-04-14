from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.date_utils import trade_date_dt_param
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
            {
                "key": "pattern",
                "label": "形态筛选",
                "value_type": "enum",
                "operators": ["="],
                "description": "形态类型（如 HAMMER、HEAD_SHOULDERS、INVERSE_HEAD_SHOULDERS）",
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

    @staticmethod
    def _normalize_pattern_filters(conditions: dict[str, Any]) -> list[str]:
        raw_pattern = conditions.get("pattern")
        if raw_pattern is None:
            return []
        if isinstance(raw_pattern, (list, tuple, set)):
            values = [str(item).strip() for item in raw_pattern]
        else:
            values = [part.strip() for part in str(raw_pattern).split(",")]
        return [value for value in values if value]

    @staticmethod
    def _normalize_saved_condition_params(params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return {}
        nested_filters = params.get("filters")
        if isinstance(nested_filters, dict):
            params = nested_filters
        return {key: value for key, value in params.items() if value is not None}

    @staticmethod
    def _normalize_indicator_key(name: Any) -> str:
        return "".join(char for char in str(name or "").lower() if char.isalnum())

    @staticmethod
    def _coerce_indicator_scalar(value: Any) -> float | None:
        if value is None:
            return None
        if hasattr(value, "iloc"):
            if len(value) == 0:  # type: ignore[arg-type]
                return None
            value = value.iloc[-1]
        elif isinstance(value, (list, tuple)):
            if not value:
                return None
            value = value[-1]
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _normalize_provider_indicator_payload(self, raw: Any) -> dict[str, float | None]:
        indicator_map: dict[str, float | None] = {}

        if raw is None:
            return indicator_map

        if isinstance(raw, dict):
            for key, value in raw.items():
                normalized_key = self._normalize_indicator_key(key)
                indicator_map[normalized_key] = self._coerce_indicator_scalar(value)
            return indicator_map

        if hasattr(raw, "empty"):
            if raw.empty:
                return indicator_map
            row = raw.iloc[-1].to_dict()
            for key, value in row.items():
                normalized_key = self._normalize_indicator_key(key)
                indicator_map[normalized_key] = self._coerce_indicator_scalar(value)
        return indicator_map

    async def _load_provider_indicator_rows(
        self,
        codes: list[str],
        target_date,
    ) -> list[dict[str, Any]]:
        if not self.provider or not codes:
            return []

        indicator_rows: list[dict[str, Any]] = []
        requested_indicators = ["RSI14", "RSI", "MACD", "MACD_SIGNAL"]

        for code in codes:
            raw_payload = await self.provider.get_technicals(
                code=code,
                indicators=requested_indicators,
                start_date=target_date,
                end_date=target_date,
            )
            indicator_map = self._normalize_provider_indicator_payload(raw_payload)
            if not indicator_map:
                continue
            indicator_rows.append(
                {
                    "code": code,
                    "rsi": indicator_map.get("rsi14", indicator_map.get("rsi")),
                    "macd": indicator_map.get("macd"),
                    "macd_signal": indicator_map.get("macdsignal"),
                }
            )

        return indicator_rows

    async def _load_pattern_hits(
        self, trade_date: str, ts_codes: list[str], pattern_names: list[str] | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        if not self.db or not ts_codes:
            return {}

        params: dict[str, Any] = {
            "trade_date": trade_date,
            "trade_date_dt": trade_date_dt_param(trade_date),
        }
        ts_placeholders: list[str] = []
        for index, ts_code in enumerate(ts_codes):
            key = f"ts_code_{index}"
            ts_placeholders.append(f":{key}")
            params[key] = ts_code

        pattern_clause = ""
        if pattern_names:
            pattern_placeholders: list[str] = []
            for index, pattern_name in enumerate(pattern_names):
                key = f"pattern_name_{index}"
                pattern_placeholders.append(f":{key}")
                params[key] = pattern_name
            pattern_clause = f" AND pattern_name IN ({', '.join(pattern_placeholders)})"

        query = text(f"""
            SELECT ts_code, pattern_name, pattern_type, confidence
            FROM patterns
            WHERE (trade_date_dt = :trade_date_dt OR (trade_date_dt IS NULL AND trade_date = :trade_date))
              AND ts_code IN ({', '.join(ts_placeholders)})
              {pattern_clause}
            ORDER BY confidence DESC NULLS LAST, pattern_name ASC
            """)
        result = await self.db.execute(query, params)
        pattern_hits: dict[str, list[dict[str, Any]]] = {}
        for row in result.mappings().all():
            ts_code = str(row.get("ts_code") or "")
            if not ts_code:
                continue
            pattern_hits.setdefault(ts_code, []).append(dict(row))
        return pattern_hits

    async def _resolve_trade_date(self, date: str | None) -> str | None:
        if not self.db:
            return None
        if date:
            target_date_dt = trade_date_dt_param(date)
            result = await self.db.execute(
                text("""
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date_dt <= :target_date_dt
                       OR (trade_date_dt IS NULL AND trade_date <= :target_date)
                    """),
                {"target_date": date, "target_date_dt": target_date_dt},
            )
        else:
            result = await self.db.execute(
                text("""
                    SELECT trade_date AS resolved_date
                    FROM daily_bars
                    ORDER BY
                        CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END,
                        trade_date_dt DESC,
                        trade_date DESC
                    LIMIT 1
                    """)
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
        condition_id: str | None = None,
        condition_name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "value": (
                round(float(actual_value), 4)
                if isinstance(actual_value, (int, float))
                else actual_value
            ),
            "operator": operator,
            "condition": SelectionService._format_condition_value(key, condition),
            "matched": True,
            "condition_id": condition_id,
            "condition_name": condition_name or label,
            "description": description or f"{label} {operator} {condition}",
        }

    def _build_reason(
        self,
        conditions: dict[str, Any],
        row: dict[str, Any],
        pattern_hits: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        pct = float(row["pct_chg"] or 0)
        amount = float(row["amount"] or 0)
        close = float(row["close"] or 0)
        market_value = "sh" if str(row["ts_code"]).endswith(".SH") else "sz"
        evidence: list[dict[str, Any]] = []
        summary_parts: list[str] = []
        selected_patterns = self._normalize_pattern_filters(conditions)

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
                    condition_id="price_min",
                    condition_name="最低价格",
                    description=f"收盘价不低于 {value:.2f}",
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
                    condition_id="price_max",
                    condition_name="最高价格",
                    description=f"收盘价不高于 {value:.2f}",
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
                    condition_id="change_min",
                    condition_name="最小涨跌幅",
                    description=f"日涨跌幅不低于 {value:.2f}%",
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
                    condition_id="change_max",
                    condition_name="最大涨跌幅",
                    description=f"日涨跌幅不高于 {value:.2f}%",
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
                    "condition_id": "market",
                    "condition_name": "市场范围",
                    "description": f"股票属于 {conditions['market']} 市场",
                }
            )

        if pattern_hits:
            matched_names = [
                str(hit.get("pattern_name") or "").strip()
                for hit in pattern_hits
                if hit.get("pattern_name")
            ]
            matched_names = [name for name in matched_names if name]
            if matched_names:
                summary_parts.append(f"Pattern = {', '.join(matched_names[:3])}")
                evidence.append(
                    {
                        "key": "pattern",
                        "label": "Pattern",
                        "value": ", ".join(matched_names[:3]),
                        "operator": "=",
                        "condition": (
                            ", ".join(selected_patterns[:3])
                            if selected_patterns
                            else ", ".join(matched_names[:3])
                        ),
                        "matched": True,
                        "condition_id": "pattern",
                        "condition_name": "形态筛选",
                        "description": f"命中形态 {', '.join(matched_names[:3])}",
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
                        condition_id="rsi_min",
                        condition_name="RSI 下限",
                        description=f"RSI 不低于 {value:.0f}",
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
                        condition_id="rsi_max",
                        condition_name="RSI 上限",
                        description=f"RSI 不高于 {value:.0f}",
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
                    "condition_id": "macd_bullish",
                    "condition_name": "MACD 看涨",
                    "description": "MACD 线位于信号线上方（金叉倾向）",
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
                    "condition_id": "macd_bearish",
                    "condition_name": "MACD 看跌",
                    "description": "MACD 线位于信号线下方（死叉倾向）",
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
        pattern_names = self._normalize_pattern_filters(conditions)

        if pattern_names:
            return await self._run_selection_with_sql(conditions, date, limit)

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
        pattern_names = self._normalize_pattern_filters(conditions)

        where_sql = [
            "s.list_status = 'L'",
            "s.is_etf = false",
            "(db.trade_date_dt = :trade_date_dt OR (db.trade_date_dt IS NULL AND db.trade_date = :trade_date))",
        ]
        params: dict[str, Any] = {
            "trade_date": trade_date,
            "trade_date_dt": trade_date_dt_param(trade_date),
        }

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
        if pattern_names:
            pattern_placeholders: list[str] = []
            for index, pattern_name in enumerate(pattern_names):
                key = f"pattern_name_{index}"
                pattern_placeholders.append(f":{key}")
                params[key] = pattern_name
            where_sql.append(f"""
                EXISTS (
                    SELECT 1
                    FROM patterns p
                    WHERE p.ts_code = s.ts_code
                      AND (p.trade_date_dt = :trade_date_dt OR (p.trade_date_dt IS NULL AND p.trade_date = :trade_date))
                      AND p.pattern_name IN ({', '.join(pattern_placeholders)})
                )
                """)

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
        """.format(where_clause=" AND ".join(where_sql))

        # If indicator filters are active, we need to join indicators table
        if rsi_min is not None or rsi_max is not None or macd_bullish or macd_bearish:
            # Add indicator joins using conditional aggregation or subqueries
            select_fields += """,
            COALESCE(MAX(CASE WHEN i.indicator_name IN ('RSI', 'RSI14') THEN i.indicator_value END), 0) AS rsi,
            COALESCE(MAX(CASE WHEN i.indicator_name = 'MACD' THEN i.indicator_value END), 0) AS macd,
            COALESCE(MAX(CASE WHEN i.indicator_name = 'MACD_SIGNAL' THEN i.indicator_value END), 0) AS macd_signal
            """
            from_clause = """
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            LEFT JOIN indicators i ON s.ts_code = i.ts_code
              AND (
                i.trade_date_dt = db.trade_date_dt
                OR (i.trade_date_dt IS NULL AND db.trade_date_dt IS NULL AND i.trade_date = db.trade_date)
              )
            WHERE {where_clause}
            GROUP BY s.ts_code, s.symbol, s.name, db.trade_date, db.close, db.pct_chg, db.vol, db.amount
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :limit
            """.format(where_clause=" AND ".join(where_sql))
        else:
            from_clause = """
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            WHERE {where_clause}
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :limit
            """.format(where_clause=" AND ".join(where_sql))

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

        pattern_hits_map: dict[str, list[dict[str, Any]]] = {}
        if pattern_names and rows:
            ts_codes = [str(row["ts_code"]) for row in rows if row.get("ts_code")]
            pattern_hits_map = await self._load_pattern_hits(trade_date, ts_codes, pattern_names)
            rows = [row for row in rows if pattern_hits_map.get(str(row["ts_code"]))]
            if not rows:
                return []

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
            reason = self._build_reason(
                conditions, dict(row), pattern_hits_map.get(str(row["ts_code"]))
            )
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

    async def get_today_summary(
        self, user_id: int, date: str | None = None, limit: int = 5
    ) -> dict[str, Any]:
        if not self.db:
            return {
                "trade_date": None,
                "total_conditions": 0,
                "active_conditions": 0,
                "total_hits": 0,
                "items": [],
            }

        trade_date = await self._resolve_trade_date(date)
        if not trade_date:
            return {
                "trade_date": None,
                "total_conditions": 0,
                "active_conditions": 0,
                "total_hits": 0,
                "items": [],
            }

        from app.models.stock_model import SelectionCondition

        stmt = (
            select(SelectionCondition)
            .where(SelectionCondition.user_id == user_id)
            .order_by(SelectionCondition.id.asc())
        )
        result = await self.db.execute(stmt)
        all_conditions = result.scalars().all()
        conditions = [condition for condition in all_conditions if condition.is_active]

        items: list[dict[str, Any]] = []
        total_hits = 0

        for condition in conditions:
            filters = self._normalize_saved_condition_params(condition.params)
            hits = await self._run_selection_with_sql(filters, trade_date, limit=1000)
            total_hits += len(hits)
            items.append(
                {
                    "condition_id": condition.id,
                    "name": condition.name,
                    "category": condition.category,
                    "description": condition.description,
                    "pattern": filters.get("pattern"),
                    "hit_count": len(hits),
                    "top_hits": [
                        {
                            "code": hit["code"],
                            "stock_name": hit.get("stock_name"),
                            "trade_date": hit.get("trade_date"),
                            "score": float(hit.get("score") or 0),
                            "signal": hit.get("signal", "hold"),
                            "reason_summary": hit.get("reason_summary"),
                        }
                        for hit in hits[:limit]
                    ],
                }
            )

        return {
            "trade_date": trade_date,
            "total_conditions": len(all_conditions),
            "active_conditions": len(conditions),
            "total_hits": total_hits,
            "items": items,
        }

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
                top_by_selection[sel_id].append(
                    {
                        "selection_id": sel_id,
                        "ts_code": row["ts_code"],
                        "code": row["code"],
                        "stock_name": row["stock_name"],
                        "trade_date": row["trade_date"],
                        "date": row["trade_date"],
                        "score": float(row["score"] or 0),
                        "signal": "hold",
                        "reason_summary": None,
                    }
                )

        # Build response items
        comparison_items: list[dict[str, Any]] = []
        for sel_id in history_ids:
            agg = aggregates.get(sel_id)
            if not agg:
                continue
            comparison_items.append(
                {
                    "history_id": sel_id,
                    "trade_date": agg["trade_date"],
                    "total": int(agg["total"]),
                    "avg_score": round(float(agg["avg_score"] or 0), 4),
                    "top_stocks": top_by_selection.get(sel_id, []),
                }
            )

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
        from datetime import date as date_cls

        import pandas as pd

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
            final_codes = filtered["code"].dropna().astype(str).unique().tolist()
            indicator_rows = await self._load_provider_indicator_rows(final_codes, target_date)
            if not indicator_rows:
                raise RuntimeError("provider technical indicators unavailable")

            technicals_df = pd.DataFrame(indicator_rows)
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
            raise

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
                evidence.append(
                    {
                        "key": "close",
                        "label": "Close",
                        "value": close,
                        "operator": ">=",
                        "condition": float(conditions["priceMin"]),
                        "matched": close >= float(conditions["priceMin"]),
                    }
                )
            if conditions.get("priceMax") is not None:
                evidence.append(
                    {
                        "key": "close",
                        "label": "Close",
                        "value": close,
                        "operator": "<=",
                        "condition": float(conditions["priceMax"]),
                        "matched": close <= float(conditions["priceMax"]),
                    }
                )
            if conditions.get("changeMin") is not None:
                evidence.append(
                    {
                        "key": "change_rate",
                        "label": "Daily change",
                        "value": round(pct, 4),
                        "operator": ">=",
                        "condition": float(conditions["changeMin"]),
                        "matched": pct >= float(conditions["changeMin"]),
                    }
                )
            if conditions.get("changeMax") is not None:
                evidence.append(
                    {
                        "key": "change_rate",
                        "label": "Daily change",
                        "value": round(pct, 4),
                        "operator": "<=",
                        "condition": float(conditions["changeMax"]),
                        "matched": pct <= float(conditions["changeMax"]),
                    }
                )

            if evidence:
                summary = "; ".join(
                    f"{e['label']} {e['operator']} {e['condition']}" for e in evidence
                )
            else:
                summary = f"Included in screening (pct_chg={pct:.2f}%)"

            score = round(pct * 5 + min(amount / 1e8, 20), 4)
            signal = "buy" if pct >= 2 else ("sell" if pct <= -2 else "hold")

            results.append(
                {
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
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results
