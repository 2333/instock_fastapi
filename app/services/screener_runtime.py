from __future__ import annotations

from typing import Any, Callable

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.date_utils import trade_date_dt_param
from app.services.screener_adapter import definition_to_filters, get_resolved_predicates, validate_definition

try:
    import talib as tl
except Exception:  # pragma: no cover - only hit when TA-Lib is unavailable
    tl = None


_RSI_RULE_KEYS = {"rsiMin", "rsiMax"}
_MACD_RULE_KEYS = {"macdBullish", "macdBearish"}
_BOLL_RULE_KEYS = {"bollCloseAboveUpper", "bollCloseBelowLower"}
_TECHNICAL_RULE_KEYS = _RSI_RULE_KEYS | _MACD_RULE_KEYS | _BOLL_RULE_KEYS


def compile_runtime_plan(definition: Any) -> dict[str, Any]:
    model = validate_definition(definition)
    resolved_predicates = get_resolved_predicates(model)
    return {
        "definition": model.model_dump(by_alias=True, exclude_none=True),
        "basic_filters": definition_to_filters(model),
        "resolved_predicates": resolved_predicates,
        "lookback_bars": BaselineSQLScreenerRuntime._calculate_lookback_bars(resolved_predicates),
    }


def evaluate_technical_rules(plan: dict[str, Any], bars: list[dict[str, Any]]) -> dict[str, Any]:
    runtime = BaselineSQLScreenerRuntime(db=None)  # type: ignore[arg-type]
    snapshot = runtime._build_indicator_snapshot(
        rows=bars,
        resolved_predicates=plan.get("resolved_predicates", []),
    )
    latest_close = float(bars[-1]["close"]) if bars else 0.0
    matched = runtime._row_matches(
        row={"close": latest_close, "pct_chg": 0},
        pattern_hits=[],
        resolved_predicates=plan.get("resolved_predicates", []),
        indicator_snapshot=snapshot,
    )
    if not matched:
        return {"matched": False, "summary_parts": [], "evidence": []}

    summary_parts: list[str] = []
    evidence: list[dict[str, Any]] = []
    cache = snapshot.get("cache", {})
    for predicate in plan.get("resolved_predicates", []):
        rule_key = predicate["rule_key"]
        params = predicate["params"]
        if rule_key in _RSI_RULE_KEYS:
            actual = cache.get(("rsi", int(params.get("period", 14))))
            if actual is None:
                continue
            summary_parts.append(f"RSI({int(params.get('period', 14))})")
            evidence.append(
                {
                    "key": "rsi",
                    "condition_id": rule_key,
                    "value": round(float(actual), 4),
                }
            )
        elif rule_key in _MACD_RULE_KEYS:
            actual = cache.get(
                (
                    "macd",
                    int(params.get("fast_period", 12)),
                    int(params.get("slow_period", 26)),
                    int(params.get("signal_period", 9)),
                )
            )
            if actual is None:
                continue
            summary_parts.append(
                "MACD"
                f"({int(params.get('fast_period', 12))},{int(params.get('slow_period', 26))},{int(params.get('signal_period', 9))})"
            )
            evidence.append(
                {
                    "key": "macd",
                    "condition_id": rule_key,
                    "value": round(float(actual[0] or 0), 4),
                }
            )
        elif rule_key in _BOLL_RULE_KEYS:
            actual = cache.get(
                (
                    "boll",
                    int(params.get("period", 20)),
                    float(params.get("stddev", 2.0)),
                )
            )
            if actual is None:
                continue
            summary_parts.append(
                f"BOLL({int(params.get('period', 20))},{float(params.get('stddev', 2.0)):g})"
            )
            evidence.append(
                {
                    "key": "close",
                    "condition_id": rule_key,
                    "value": round(latest_close, 4),
                }
            )
    return {"matched": True, "summary_parts": summary_parts, "evidence": evidence}


class BaselineSQLScreenerRuntime:
    """Run canonical saved screener definitions on the current SQL-backed stack."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        *,
        definition: Any,
        trade_date: str,
        limit: int = 300,
        reason_builder: Callable[[dict[str, Any], dict[str, Any], list[dict[str, Any]] | None], dict[str, Any]]
        | None = None,
    ) -> list[dict[str, Any]]:
        model = validate_definition(definition)
        filters = definition_to_filters(model)
        resolved_predicates = get_resolved_predicates(model)
        uses_technical_rules = any(
            predicate["rule_key"] in _TECHNICAL_RULE_KEYS for predicate in resolved_predicates
        )

        rows = await self._load_current_rows(
            filters=filters,
            trade_date=trade_date,
            limit=limit,
            overfetch=uses_technical_rules,
        )
        if not rows:
            return []

        ts_codes = [str(row["ts_code"]) for row in rows if row.get("ts_code")]
        pattern_names = self._normalize_pattern_filters(filters)
        pattern_hits_map: dict[str, list[dict[str, Any]]] = {}
        if pattern_names and ts_codes:
            pattern_hits_map = await self._load_pattern_hits(trade_date, ts_codes, pattern_names)

        indicator_snapshots: dict[str, dict[str, Any]] = {}
        if uses_technical_rules and ts_codes:
            indicator_snapshots = await self._load_indicator_snapshots(
                ts_codes=ts_codes,
                trade_date=trade_date,
                resolved_predicates=resolved_predicates,
            )
            indicator_fallbacks = await self._load_indicator_fallback_rows(ts_codes, trade_date)
            indicator_snapshots = self._apply_indicator_fallbacks(
                indicator_snapshots=indicator_snapshots,
                indicator_fallbacks=indicator_fallbacks,
                resolved_predicates=resolved_predicates,
            )

        results: list[dict[str, Any]] = []
        for row in rows:
            ts_code = str(row.get("ts_code") or "")
            pattern_hits = pattern_hits_map.get(ts_code, [])
            indicator_snapshot = indicator_snapshots.get(ts_code, {"cache": {}})
            if not self._matches_scope_market(model.scope.market, ts_code):
                continue
            if not self._row_matches(
                row=row,
                pattern_hits=pattern_hits,
                resolved_predicates=resolved_predicates,
                indicator_snapshot=indicator_snapshot,
            ):
                continue

            enriched_row = dict(row)
            enriched_row.update(
                {
                    key: value
                    for key, value in indicator_snapshot.items()
                    if key != "cache" and value is not None
                }
            )
            reason = (
                reason_builder(filters, enriched_row, pattern_hits)
                if reason_builder
                else self._build_default_reason(filters)
            )
            results.append(self._format_result(enriched_row, reason))
            if len(results) >= limit:
                break

        return results

    async def _load_current_rows(
        self,
        *,
        filters: dict[str, Any],
        trade_date: str,
        limit: int,
        overfetch: bool,
    ) -> list[dict[str, Any]]:
        where_sql = [
            "s.list_status = 'L'",
            "s.is_etf = false",
            "(db.trade_date_dt = :trade_date_dt OR (db.trade_date_dt IS NULL AND db.trade_date = :trade_date))",
        ]
        params: dict[str, Any] = {
            "trade_date": trade_date,
            "trade_date_dt": trade_date_dt_param(trade_date),
        }

        if filters.get("priceMin") is not None:
            where_sql.append("db.close >= :price_min")
            params["price_min"] = float(filters["priceMin"])
        if filters.get("priceMax") is not None:
            where_sql.append("db.close <= :price_max")
            params["price_max"] = float(filters["priceMax"])
        if filters.get("changeMin") is not None:
            where_sql.append("db.pct_chg >= :change_min")
            params["change_min"] = float(filters["changeMin"])
        if filters.get("changeMax") is not None:
            where_sql.append("db.pct_chg <= :change_max")
            params["change_max"] = float(filters["changeMax"])
        if filters.get("market") == "sh":
            where_sql.append("s.symbol LIKE '6%'")
        elif filters.get("market") == "sz":
            where_sql.append("(s.symbol LIKE '0%' OR s.symbol LIKE '3%')")

        pattern_names = self._normalize_pattern_filters(filters)
        if pattern_names:
            placeholders: list[str] = []
            for index, pattern_name in enumerate(pattern_names):
                key = f"pattern_name_{index}"
                placeholders.append(f":{key}")
                params[key] = pattern_name
            where_sql.append(f"""
                EXISTS (
                    SELECT 1
                    FROM patterns p
                    WHERE p.ts_code = s.ts_code
                      AND (p.trade_date_dt = :trade_date_dt OR (p.trade_date_dt IS NULL AND p.trade_date = :trade_date))
                      AND p.pattern_name IN ({', '.join(placeholders)})
                )
            """)

        candidate_limit = limit
        if overfetch:
            candidate_limit = max(limit, min(limit * 5, 1000))
        params["candidate_limit"] = candidate_limit

        query = text(f"""
            SELECT
                s.ts_code,
                s.symbol AS code,
                s.name AS stock_name,
                db.trade_date,
                db.close,
                db.pct_chg,
                db.vol,
                db.amount
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            WHERE {' AND '.join(where_sql)}
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :candidate_limit
        """)
        result = await self.db.execute(query, params)
        return [dict(row) for row in result.mappings().all()]

    async def _load_pattern_hits(
        self,
        trade_date: str,
        ts_codes: list[str],
        pattern_names: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        if not ts_codes:
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

        pattern_placeholders: list[str] = []
        for index, pattern_name in enumerate(pattern_names):
            key = f"pattern_name_{index}"
            pattern_placeholders.append(f":{key}")
            params[key] = pattern_name

        query = text(f"""
            SELECT ts_code, pattern_name, pattern_type, confidence
            FROM patterns
            WHERE (trade_date_dt = :trade_date_dt OR (trade_date_dt IS NULL AND trade_date = :trade_date))
              AND ts_code IN ({', '.join(ts_placeholders)})
              AND pattern_name IN ({', '.join(pattern_placeholders)})
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

    async def _load_indicator_snapshots(
        self,
        *,
        ts_codes: list[str],
        trade_date: str,
        resolved_predicates: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        history_rows = await self._load_history_rows(ts_codes, trade_date)
        if not history_rows:
            return {}

        lookback_bars = self._calculate_lookback_bars(resolved_predicates)
        by_code: dict[str, list[dict[str, Any]]] = {}
        for row in history_rows:
            ts_code = str(row.get("ts_code") or "")
            if not ts_code:
                continue
            by_code.setdefault(ts_code, []).append(row)

        snapshots: dict[str, dict[str, Any]] = {}
        for ts_code, rows in by_code.items():
            snapshots[ts_code] = self._build_indicator_snapshot(
                rows=rows[-lookback_bars:],
                resolved_predicates=resolved_predicates,
            )
        return snapshots

    async def _load_history_rows(self, ts_codes: list[str], trade_date: str) -> list[dict[str, Any]]:
        if not ts_codes:
            return []

        params: dict[str, Any] = {"trade_date": trade_date}
        placeholders: list[str] = []
        for index, ts_code in enumerate(ts_codes):
            key = f"history_ts_code_{index}"
            placeholders.append(f":{key}")
            params[key] = ts_code

        query = text(f"""
            SELECT ts_code, trade_date, open, high, low, close
            FROM daily_bars
            WHERE ts_code IN ({', '.join(placeholders)})
              AND trade_date <= :trade_date
            ORDER BY ts_code ASC, trade_date ASC
        """)
        result = await self.db.execute(query, params)
        return [dict(row) for row in result.mappings().all()]

    async def _load_indicator_fallback_rows(
        self,
        ts_codes: list[str],
        trade_date: str,
    ) -> dict[str, dict[str, Any]]:
        if not ts_codes:
            return {}

        params: dict[str, Any] = {
            "trade_date": trade_date,
            "trade_date_dt": trade_date_dt_param(trade_date),
        }
        placeholders: list[str] = []
        for index, ts_code in enumerate(ts_codes):
            key = f"indicator_ts_code_{index}"
            placeholders.append(f":{key}")
            params[key] = ts_code

        query = text(f"""
            SELECT
                ts_code,
                MAX(CASE WHEN indicator_name IN ('RSI', 'RSI14') THEN indicator_value END) AS rsi,
                MAX(CASE WHEN indicator_name = 'MACD' THEN indicator_value END) AS macd,
                MAX(CASE WHEN indicator_name = 'MACD_SIGNAL' THEN indicator_value END) AS macd_signal,
                MAX(CASE WHEN indicator_name = 'BOLL_UPPER' THEN indicator_value END) AS boll_upper,
                MAX(CASE WHEN indicator_name = 'BOLL_LOWER' THEN indicator_value END) AS boll_lower
            FROM indicators
            WHERE ts_code IN ({', '.join(placeholders)})
              AND (trade_date_dt = :trade_date_dt OR (trade_date_dt IS NULL AND trade_date = :trade_date))
            GROUP BY ts_code
        """)
        result = await self.db.execute(query, params)
        return {
            str(row["ts_code"]): dict(row)
            for row in result.mappings().all()
            if row.get("ts_code")
        }

    def _build_indicator_snapshot(
        self,
        *,
        rows: list[dict[str, Any]],
        resolved_predicates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        closes = np.asarray([float(row.get("close") or 0) for row in rows], dtype=float)
        cache: dict[tuple[Any, ...], Any] = {}
        snapshot: dict[str, Any] = {"cache": cache}

        for predicate in resolved_predicates:
            rule_key = predicate["rule_key"]
            params = predicate["params"]

            if rule_key in _RSI_RULE_KEYS:
                period = int(params.get("period", 14))
                signature = ("rsi", period)
                if signature not in cache:
                    cache[signature] = self._calculate_rsi(closes, period)
                if snapshot.get("rsi") is None and cache[signature] is not None:
                    snapshot["rsi"] = cache[signature]
                continue

            if rule_key in _MACD_RULE_KEYS:
                fast_period = int(params.get("fast_period", 12))
                slow_period = int(params.get("slow_period", 26))
                signal_period = int(params.get("signal_period", 9))
                signature = ("macd", fast_period, slow_period, signal_period)
                if signature not in cache:
                    cache[signature] = self._calculate_macd(
                        closes,
                        fast_period=fast_period,
                        slow_period=slow_period,
                        signal_period=signal_period,
                    )
                if snapshot.get("macd") is None and cache[signature] is not None:
                    snapshot["macd"], snapshot["macd_signal"] = cache[signature]
                continue

            if rule_key in _BOLL_RULE_KEYS:
                period = int(params.get("period", 20))
                stddev = float(params.get("stddev", 2.0))
                signature = ("boll", period, stddev)
                if signature not in cache:
                    cache[signature] = self._calculate_bbands(
                        closes,
                        period=period,
                        stddev=stddev,
                    )
                if snapshot.get("boll_upper") is None and cache[signature] is not None:
                    snapshot["boll_upper"], snapshot["boll_lower"] = cache[signature]

        return snapshot

    def _apply_indicator_fallbacks(
        self,
        *,
        indicator_snapshots: dict[str, dict[str, Any]],
        indicator_fallbacks: dict[str, dict[str, Any]],
        resolved_predicates: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        snapshots = {ts_code: dict(snapshot) for ts_code, snapshot in indicator_snapshots.items()}

        for ts_code, fallback in indicator_fallbacks.items():
            snapshot = snapshots.setdefault(ts_code, {"cache": {}})
            cache = snapshot.setdefault("cache", {})

            for predicate in resolved_predicates:
                rule_key = predicate["rule_key"]
                params = predicate["params"]

                if rule_key in _RSI_RULE_KEYS and self._is_default_rsi_params(params):
                    rsi_value = fallback.get("rsi")
                    if rsi_value is not None:
                        if cache.get(("rsi", 14)) is None:
                            cache[("rsi", 14)] = float(rsi_value)
                        if snapshot.get("rsi") is None:
                            snapshot["rsi"] = float(rsi_value)

                if rule_key in _MACD_RULE_KEYS and self._is_default_macd_params(params):
                    macd_value = fallback.get("macd")
                    if macd_value is not None:
                        signal_value = fallback.get("macd_signal")
                        normalized_signal = (
                            float(signal_value)
                            if signal_value is not None
                            else 0.0
                        )
                        cached_macd = cache.get(("macd", 12, 26, 9))
                        if cached_macd is None or cached_macd[0] is None or cached_macd[1] is None:
                            cache[("macd", 12, 26, 9)] = (
                                float(macd_value),
                                normalized_signal,
                            )
                        if snapshot.get("macd") is None:
                            snapshot["macd"] = float(macd_value)
                        if snapshot.get("macd_signal") is None:
                            snapshot["macd_signal"] = normalized_signal

                if rule_key in _BOLL_RULE_KEYS and self._is_default_boll_params(params):
                    upper_band = fallback.get("boll_upper")
                    lower_band = fallback.get("boll_lower")
                    if upper_band is not None or lower_band is not None:
                        cached_boll = cache.get(("boll", 20, 2.0))
                        if cached_boll is None or cached_boll[0] is None or cached_boll[1] is None:
                            cache[("boll", 20, 2.0)] = (
                                float(upper_band) if upper_band is not None else None,
                                float(lower_band) if lower_band is not None else None,
                            )
                        if upper_band is not None and snapshot.get("boll_upper") is None:
                            snapshot["boll_upper"] = float(upper_band)
                        if lower_band is not None and snapshot.get("boll_lower") is None:
                            snapshot["boll_lower"] = float(lower_band)

        return snapshots

    def _row_matches(
        self,
        *,
        row: dict[str, Any],
        pattern_hits: list[dict[str, Any]],
        resolved_predicates: list[dict[str, Any]],
        indicator_snapshot: dict[str, Any],
    ) -> bool:
        close = float(row.get("close") or 0)
        pct_chg = float(row.get("pct_chg") or 0)
        cache = indicator_snapshot.get("cache", {})

        for predicate in resolved_predicates:
            rule_key = predicate["rule_key"]
            params = predicate["params"]
            expected = params.get("value")

            if rule_key == "priceMin" and close < float(expected):
                return False
            if rule_key == "priceMax" and close > float(expected):
                return False
            if rule_key == "changeMin" and pct_chg < float(expected):
                return False
            if rule_key == "changeMax" and pct_chg > float(expected):
                return False
            if rule_key == "pattern":
                expected_names = self._normalize_pattern_filters({"pattern": expected})
                actual_names = {
                    str(hit.get("pattern_name") or "").strip()
                    for hit in pattern_hits
                    if hit.get("pattern_name")
                }
                if not actual_names.intersection(expected_names):
                    return False
            if rule_key in _RSI_RULE_KEYS:
                actual = cache.get(("rsi", int(params.get("period", 14))))
                if actual is None:
                    return False
                if rule_key == "rsiMin" and actual < float(expected):
                    return False
                if rule_key == "rsiMax" and actual > float(expected):
                    return False
            if rule_key in _MACD_RULE_KEYS:
                if expected is False:
                    continue
                signature = (
                    "macd",
                    int(params.get("fast_period", 12)),
                    int(params.get("slow_period", 26)),
                    int(params.get("signal_period", 9)),
                )
                actual = cache.get(signature)
                if actual is None:
                    return False
                macd_value, signal_value = actual
                if macd_value is None or signal_value is None:
                    return False
                if rule_key == "macdBullish" and macd_value <= signal_value:
                    return False
                if rule_key == "macdBearish" and macd_value >= signal_value:
                    return False
            if rule_key in _BOLL_RULE_KEYS:
                if expected is False:
                    continue
                signature = (
                    "boll",
                    int(params.get("period", 20)),
                    float(params.get("stddev", 2.0)),
                )
                actual = cache.get(signature)
                if actual is None:
                    return False
                upper_band, lower_band = actual
                if rule_key == "bollCloseAboveUpper" and (
                    upper_band is None or close <= upper_band
                ):
                    return False
                if rule_key == "bollCloseBelowLower" and (
                    lower_band is None or close >= lower_band
                ):
                    return False

        return True

    @staticmethod
    def _matches_scope_market(scope_market: str | None, ts_code: str) -> bool:
        if not scope_market:
            return True
        suffix = ts_code.upper()
        if scope_market == "sh":
            return suffix.endswith(".SH")
        if scope_market == "sz":
            return suffix.endswith(".SZ")
        return True

    @staticmethod
    def _normalize_pattern_filters(filters: dict[str, Any]) -> list[str]:
        raw_pattern = filters.get("pattern")
        if raw_pattern is None:
            return []
        if isinstance(raw_pattern, (list, tuple, set)):
            values = [str(item).strip() for item in raw_pattern]
        else:
            values = [part.strip() for part in str(raw_pattern).split(",")]
        return [value for value in values if value]

    @staticmethod
    def _is_default_rsi_params(params: dict[str, Any]) -> bool:
        return int(params.get("period", 14)) == 14

    @staticmethod
    def _is_default_macd_params(params: dict[str, Any]) -> bool:
        return (
            int(params.get("fast_period", 12)) == 12
            and int(params.get("slow_period", 26)) == 26
            and int(params.get("signal_period", 9)) == 9
        )

    @staticmethod
    def _is_default_boll_params(params: dict[str, Any]) -> bool:
        return int(params.get("period", 20)) == 20 and float(params.get("stddev", 2.0)) == 2.0

    @staticmethod
    def _calculate_lookback_bars(resolved_predicates: list[dict[str, Any]]) -> int:
        lookback_bars = 2
        for predicate in resolved_predicates:
            params = predicate["params"]
            rule_key = predicate["rule_key"]
            if rule_key in _RSI_RULE_KEYS:
                lookback_bars = max(lookback_bars, int(params.get("period", 14)) + 5)
            if rule_key in _MACD_RULE_KEYS:
                lookback_bars = max(
                    lookback_bars,
                    int(params.get("slow_period", 26)) + int(params.get("signal_period", 9)) + 10,
                )
            if rule_key in _BOLL_RULE_KEYS:
                lookback_bars = max(lookback_bars, int(params.get("period", 20)) + 5)
        return lookback_bars

    @staticmethod
    def _last_finite(values: Any) -> float | None:
        array = np.asarray(values, dtype=float)
        if array.size == 0:
            return None
        for value in array[::-1]:
            if np.isfinite(value):
                return float(value)
        return None

    def _calculate_rsi(self, closes: np.ndarray, period: int) -> float | None:
        if tl is None or len(closes) < max(period + 1, 3):
            return None
        return self._last_finite(tl.RSI(closes, timeperiod=period))

    def _calculate_macd(
        self,
        closes: np.ndarray,
        *,
        fast_period: int,
        slow_period: int,
        signal_period: int,
    ) -> tuple[float | None, float | None] | None:
        if tl is None or len(closes) < max(slow_period + signal_period, slow_period + 2):
            return None
        macd, signal, _hist = tl.MACD(
            closes,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period,
        )
        return self._last_finite(macd), self._last_finite(signal)

    def _calculate_bbands(
        self,
        closes: np.ndarray,
        *,
        period: int,
        stddev: float,
    ) -> tuple[float | None, float | None] | None:
        if tl is None or len(closes) < period:
            return None
        upper, _middle, lower = tl.BBANDS(
            closes,
            timeperiod=period,
            nbdevup=stddev,
            nbdevdn=stddev,
            matype=0,
        )
        return self._last_finite(upper), self._last_finite(lower)

    @staticmethod
    def _build_default_reason(filters: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": f"Matched canonical screener with {len(filters)} resolved filters",
            "evidence": [],
        }

    @staticmethod
    def _format_result(row: dict[str, Any], reason: dict[str, Any]) -> dict[str, Any]:
        pct = float(row.get("pct_chg") or 0)
        amount = float(row.get("amount") or 0)
        score = pct * 5 + min(amount / 1e8, 20)
        signal = "hold"
        if pct >= 2:
            signal = "buy"
        elif pct <= -2:
            signal = "sell"
        return {
            "ts_code": row["ts_code"],
            "code": row["code"],
            "stock_name": row["stock_name"],
            "score": round(score, 4),
            "signal": signal,
            "trade_date": row["trade_date"],
            "date": row["trade_date"],
            "close": float(row.get("close") or 0),
            "change_rate": pct,
            "amount": amount,
            "reason_summary": reason.get("summary"),
            "evidence": reason.get("evidence", []),
            "reason": reason,
        }
