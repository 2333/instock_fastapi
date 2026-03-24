from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.selection.catalog.base import SelectionCatalogRegistry
from app.selection.dsl import (
    ConditionNode,
    ConstantReference,
    GroupNode,
    MetricReference,
    SelectionNode,
    SelectionTemplatePayload,
    TimeRule,
    count_leaf_conditions,
    iter_condition_nodes,
)


@dataclass
class NodeEvaluation:
    matched: bool
    score: float
    explanations: list[dict[str, Any]]
    leaf_count: int
    matched_leaves: int


@dataclass
class StockFrame:
    ts_code: str
    code: str
    stock_name: str
    frame: pd.DataFrame


class _MetricEvaluator:
    def __init__(self, registry: SelectionCatalogRegistry, frame: pd.DataFrame):
        self.registry = registry
        self.frame = frame
        self.cache: dict[str, pd.Series] = {}

    def resolve(self, reference: MetricReference) -> pd.Series:
        definition = self.registry.get(reference.metric_key)
        output_key = reference.output_key or definition.default_output
        params = reference.params or {}
        cache_key = f"{reference.metric_key}:{output_key}:{sorted(params.items())}"
        if cache_key not in self.cache:
            series = definition.compute(self.frame, params, output_key)
            if not isinstance(series, pd.Series):
                series = pd.Series(series, index=self.frame.index)
            series = series.reindex(self.frame.index)
            self.cache[cache_key] = series
        return self.cache[cache_key]


class SelectionExecutionEngine:
    def __init__(self, db: AsyncSession, registry: SelectionCatalogRegistry):
        self.db = db
        self.registry = registry
        self._table_cache: dict[str, bool] = {}

    async def execute(
        self,
        template: SelectionTemplatePayload,
        trade_date: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        resolved_trade_date = await self._resolve_trade_date(trade_date)
        if not resolved_trade_date:
            return {
                "selection_id": None,
                "trade_date": None,
                "period": template.period,
                "matched_count": 0,
                "items": [],
            }

        stock_frames = await self._load_stock_frames(template, resolved_trade_date)
        if not stock_frames:
            return {
                "selection_id": None,
                "trade_date": resolved_trade_date,
                "period": template.period,
                "matched_count": 0,
                "items": [],
            }

        total_conditions = count_leaf_conditions(template.root)
        results: list[dict[str, Any]] = []

        for stock_frame in stock_frames:
            if stock_frame.frame.empty:
                continue
            evaluator = _MetricEvaluator(self.registry, stock_frame.frame)
            evaluation = self._evaluate_node(template.root, evaluator)
            if not evaluation.matched:
                continue
            latest_row = stock_frame.frame.iloc[-1]
            latest_trade_date = self._serialize_value(latest_row.get("trade_date")) or resolved_trade_date
            results.append(
                {
                    "ts_code": stock_frame.ts_code,
                    "code": stock_frame.code,
                    "stock_name": stock_frame.stock_name,
                    "trade_date": latest_trade_date,
                    "date": latest_trade_date,
                    "score": round(float(evaluation.score), 4),
                    "signal": self._score_signal(evaluation.score),
                    "matched_conditions": evaluation.matched_leaves,
                    "total_conditions": total_conditions,
                    "snapshot": {
                        "close": self._serialize_value(latest_row.get("close")),
                        "pct_chg": self._serialize_value(latest_row.get("pct_chg")),
                        "volume": self._serialize_value(latest_row.get("volume")),
                        "amount": self._serialize_value(latest_row.get("amount")),
                    },
                    "explanations": evaluation.explanations,
                }
            )

        results.sort(
            key=lambda item: (
                float(item.get("score") or 0),
                int(item.get("matched_conditions") or 0),
                str(item.get("code") or ""),
            ),
            reverse=True,
        )
        limited = results[: max(1, limit)]
        return {
            "selection_id": None,
            "trade_date": resolved_trade_date,
            "period": template.period,
            "matched_count": len(results),
            "items": limited,
        }

    async def _resolve_trade_date(self, target_date: str | None) -> str | None:
        if target_date:
            result = await self.db.execute(
                text(
                    """
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date <= :target_date
                    """
                ),
                {"target_date": target_date},
            )
        else:
            result = await self.db.execute(text("SELECT MAX(trade_date) AS resolved_date FROM daily_bars"))
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def _load_stock_frames(
        self, template: SelectionTemplatePayload, resolved_trade_date: str
    ) -> list[StockFrame]:
        lookback_days = self._estimate_lookback_days(template)
        end_dt = datetime.strptime(resolved_trade_date, "%Y%m%d").date()
        start_dt = end_dt - timedelta(days=lookback_days)
        start_trade_date = start_dt.strftime("%Y%m%d")

        bars = await self._load_daily_bars(start_trade_date, resolved_trade_date)
        if not bars:
            return []

        bars_df = pd.DataFrame(bars)
        bars_df["trade_date"] = pd.to_datetime(bars_df["trade_date"])
        numeric_bar_columns = ["open", "high", "low", "close", "pct_chg", "volume", "amount"]
        for column in numeric_bar_columns:
            bars_df[column] = pd.to_numeric(bars_df[column], errors="coerce")

        daily_basic_df = pd.DataFrame(await self._load_daily_basic(start_trade_date, resolved_trade_date))
        if not daily_basic_df.empty:
            daily_basic_df["trade_date"] = pd.to_datetime(daily_basic_df["trade_date"])

        patterns_df = pd.DataFrame(await self._load_patterns(start_trade_date, resolved_trade_date))
        if not patterns_df.empty:
            patterns_df["trade_date"] = pd.to_datetime(patterns_df["trade_date"])
            patterns_df["confidence"] = pd.to_numeric(patterns_df["confidence"], errors="coerce")

        frames: list[StockFrame] = []
        for ts_code, group in bars_df.groupby("ts_code"):
            group = group.sort_values("trade_date")
            price_frame = (
                group[["trade_date", "open", "high", "low", "close", "pct_chg", "volume", "amount"]]
                .drop_duplicates(subset=["trade_date"])
                .set_index("trade_date")
                .sort_index()
            )
            if price_frame.empty:
                continue
            if template.period != "daily":
                price_frame = self._resample_price_frame(price_frame, template.period)
            else:
                price_frame["pct_chg"] = price_frame["pct_chg"].fillna(price_frame["close"].pct_change() * 100)
            if price_frame.empty:
                continue

            basic_frame = self._build_basic_frame(daily_basic_df, ts_code, template.period)
            pattern_frame = self._build_pattern_frame(patterns_df, ts_code, template.period)
            merged = price_frame.join(basic_frame, how="left").join(pattern_frame, how="left")
            if merged.empty:
                continue
            for column in [col for col in merged.columns if col.startswith("pattern__")]:
                merged[column] = merged[column].fillna(False).astype(bool)
            merged["trade_date"] = merged.index.strftime("%Y%m%d")
            frames.append(
                StockFrame(
                    ts_code=ts_code,
                    code=str(group["code"].iloc[-1]),
                    stock_name=str(group["stock_name"].iloc[-1]),
                    frame=merged,
                )
            )
        return frames

    async def _load_daily_bars(self, start_trade_date: str, end_trade_date: str) -> list[dict[str, Any]]:
        result = await self.db.execute(
            text(
                """
                SELECT
                    s.ts_code,
                    s.symbol AS code,
                    s.name AS stock_name,
                    db.trade_date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pct_chg,
                    db.vol AS volume,
                    db.amount
                FROM stocks s
                JOIN daily_bars db ON s.ts_code = db.ts_code
                WHERE s.list_status = 'L'
                  AND s.is_etf = false
                  AND db.trade_date BETWEEN :start_trade_date AND :end_trade_date
                ORDER BY s.ts_code, db.trade_date
                """
            ),
            {"start_trade_date": start_trade_date, "end_trade_date": end_trade_date},
        )
        return [dict(row) for row in result.mappings().all()]

    async def _load_daily_basic(self, start_trade_date: str, end_trade_date: str) -> list[dict[str, Any]]:
        if not await self._table_exists("daily_basic"):
            return []
        result = await self.db.execute(
            text(
                """
                SELECT
                    ts_code,
                    trade_date,
                    turnover_rate,
                    turnover_rate_f,
                    volume_ratio,
                    pe,
                    pe_ttm,
                    pb,
                    ps,
                    ps_ttm,
                    dv_ratio,
                    dv_ttm,
                    total_mv,
                    circ_mv
                FROM daily_basic
                WHERE trade_date BETWEEN :start_trade_date AND :end_trade_date
                ORDER BY ts_code, trade_date
                """
            ),
            {"start_trade_date": start_trade_date, "end_trade_date": end_trade_date},
        )
        return [dict(row) for row in result.mappings().all()]

    async def _load_patterns(self, start_trade_date: str, end_trade_date: str) -> list[dict[str, Any]]:
        if not await self._table_exists("patterns"):
            return []
        result = await self.db.execute(
            text(
                """
                SELECT ts_code, trade_date, pattern_name, confidence
                FROM patterns
                WHERE trade_date BETWEEN :start_trade_date AND :end_trade_date
                ORDER BY ts_code, trade_date
                """
            ),
            {"start_trade_date": start_trade_date, "end_trade_date": end_trade_date},
        )
        return [dict(row) for row in result.mappings().all()]

    async def _table_exists(self, table_name: str) -> bool:
        if table_name in self._table_cache:
            return self._table_cache[table_name]
        connection = await self.db.connection()
        tables = await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        exists = table_name in set(tables)
        self._table_cache[table_name] = exists
        return exists

    def _estimate_lookback_days(self, template: SelectionTemplatePayload) -> int:
        estimate = 60
        for condition in iter_condition_nodes(template.root):
            estimate = max(
                estimate,
                self._estimate_reference_lookback(condition.left),
                condition.time_rule.lookback + 5,
            )
            if isinstance(condition.right, MetricReference):
                estimate = max(estimate, self._estimate_reference_lookback(condition.right))
        multiplier = {"daily": 2, "weekly": 10, "monthly": 35}[template.period]
        return max(120, estimate * multiplier)

    def _estimate_reference_lookback(self, reference: MetricReference) -> int:
        params = reference.params or {}
        key = reference.metric_key
        if key in {"open", "high", "low", "close", "pct_chg", "volume", "amount"}:
            return 2
        if key in {"pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_mv", "circ_mv", "turnover_rate", "volume_ratio"}:
            return 2
        if key.startswith("pattern__"):
            return 2
        if key in {"ma", "ema", "volume_ma"}:
            return int(params.get("period", 20) or 20) + 5
        if key == "macd":
            slow = int(params.get("slow", 26) or 26)
            signal = int(params.get("signal", 9) or 9)
            return slow + signal + 10
        if key in {"rsi", "atr", "cci"}:
            return int(params.get("period", 14) or 14) + 5
        if key == "kdj":
            return int(params.get("fastk", 9) or 9) + int(params.get("slowk", 3) or 3) + int(params.get("slowd", 3) or 3) + 5
        if key == "boll":
            return int(params.get("period", 20) or 20) + 5
        return 30

    def _resample_price_frame(self, frame: pd.DataFrame, period: str) -> pd.DataFrame:
        rule = {"weekly": "W-FRI", "monthly": "M"}[period]
        resampled = frame.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "amount": "sum",
            }
        )
        resampled = resampled.dropna(subset=["close"])
        resampled["pct_chg"] = resampled["close"].pct_change() * 100
        return resampled

    def _build_basic_frame(self, daily_basic_df: pd.DataFrame, ts_code: str, period: str) -> pd.DataFrame:
        if daily_basic_df.empty:
            return pd.DataFrame()
        subset = daily_basic_df[daily_basic_df["ts_code"] == ts_code]
        if subset.empty:
            return pd.DataFrame()
        basic_columns = [
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "pe",
            "pe_ttm",
            "pb",
            "ps",
            "ps_ttm",
            "dv_ratio",
            "dv_ttm",
            "total_mv",
            "circ_mv",
        ]
        frame = (
            subset[["trade_date", *basic_columns]]
            .drop_duplicates(subset=["trade_date"])
            .set_index("trade_date")
            .sort_index()
        )
        frame = frame.apply(pd.to_numeric, errors="coerce")
        if period == "daily":
            return frame
        rule = {"weekly": "W-FRI", "monthly": "M"}[period]
        return frame.resample(rule).last()

    def _build_pattern_frame(self, patterns_df: pd.DataFrame, ts_code: str, period: str) -> pd.DataFrame:
        if patterns_df.empty:
            return pd.DataFrame()
        subset = patterns_df[patterns_df["ts_code"] == ts_code]
        if subset.empty:
            return pd.DataFrame()
        subset = subset.assign(occurred=True)
        occurred = subset.pivot_table(
            index="trade_date",
            columns="pattern_name",
            values="occurred",
            aggfunc="max",
            fill_value=False,
        )
        occurred.columns = [f"pattern__{column}" for column in occurred.columns]
        confidence = subset.pivot_table(
            index="trade_date",
            columns="pattern_name",
            values="confidence",
            aggfunc="max",
        )
        confidence.columns = [f"pattern_conf__{column}" for column in confidence.columns]
        frame = occurred.join(confidence, how="outer").sort_index()
        if period == "daily":
            return frame
        rule = {"weekly": "W-FRI", "monthly": "M"}[period]
        bool_columns = [column for column in frame.columns if column.startswith("pattern__")]
        conf_columns = [column for column in frame.columns if column.startswith("pattern_conf__")]
        bool_frame = frame[bool_columns].resample(rule).max().astype(bool) if bool_columns else pd.DataFrame(index=frame.index)
        conf_frame = frame[conf_columns].resample(rule).max() if conf_columns else pd.DataFrame(index=frame.index)
        return bool_frame.join(conf_frame, how="outer")

    def _evaluate_node(self, node: SelectionNode, evaluator: _MetricEvaluator) -> NodeEvaluation:
        if isinstance(node, ConditionNode):
            return self._evaluate_condition(node, evaluator)
        child_results = [self._evaluate_node(child, evaluator) for child in node.children]
        explanations: list[dict[str, Any]] = []
        for child_result in child_results:
            explanations.extend(child_result.explanations)
        leaf_count = sum(child_result.leaf_count for child_result in child_results)
        matched_leaves = sum(child_result.matched_leaves for child_result in child_results)
        if node.combinator == "and":
            matched = bool(child_results) and all(child_result.matched for child_result in child_results)
            score = (
                sum(child_result.score for child_result in child_results) / len(child_results)
                if matched and child_results
                else 0.0
            )
            return NodeEvaluation(matched, round(score, 4), explanations, leaf_count, matched_leaves)
        if node.combinator == "or":
            matched_children = [child_result for child_result in child_results if child_result.matched]
            matched = bool(matched_children)
            score = max((child_result.score for child_result in matched_children), default=0.0)
            matched_leaf_total = sum(child_result.matched_leaves for child_result in matched_children)
            return NodeEvaluation(matched, round(score, 4), explanations, leaf_count, matched_leaf_total)
        child = child_results[0] if child_results else None
        matched = not child.matched if child is not None else True
        score = 100.0 if matched else 0.0
        return NodeEvaluation(matched, score, explanations, max(1, leaf_count), 1 if matched else 0)

    def _evaluate_condition(self, node: ConditionNode, evaluator: _MetricEvaluator) -> NodeEvaluation:
        left_series = evaluator.resolve(node.left)
        if isinstance(node.right, ConstantReference):
            right_value = node.right.value
            right_series = pd.Series(right_value, index=left_series.index)
            right_label = right_value
        else:
            right_series = evaluator.resolve(node.right)
            right_label = node.right.metric_key
        comparison = self._compare_series(left_series, right_series, node.operator)
        matched, timing = self._evaluate_time_rule(comparison, node.time_rule)
        latest_left = self._serialize_value(left_series.iloc[-1] if not left_series.empty else None)
        latest_right = self._serialize_value(
            right_series.iloc[-1] if not right_series.empty else getattr(node.right, "value", None)
        )
        match_index = timing.get("last_match_index")
        match_left = self._serialize_value(left_series.loc[match_index] if match_index is not None else latest_left)
        match_right = self._serialize_value(right_series.loc[match_index] if match_index is not None else latest_right)
        score = self._condition_score(
            matched=matched,
            operator=node.operator,
            time_rule=node.time_rule,
            match_left=match_left,
            match_right=match_right,
            timing=timing,
        )
        explanation = {
            "id": node.id,
            "label": node.label or node.left.metric_key,
            "metric_key": node.left.metric_key,
            "output_key": node.left.output_key or "value",
            "operator": node.operator,
            "right": right_label,
            "time_rule": {
                "mode": node.time_rule.mode,
                "lookback": node.time_rule.lookback,
            },
            "matched": matched,
            "score": round(score, 4),
            "latest_left": latest_left,
            "latest_right": latest_right,
            "match_left": match_left,
            "match_right": match_right,
            "match_count": timing.get("match_count", 0),
            "last_match_date": self._serialize_value(match_index),
        }
        return NodeEvaluation(
            matched=matched,
            score=round(score, 4),
            explanations=[explanation],
            leaf_count=1,
            matched_leaves=1 if matched else 0,
        )

    def _compare_series(self, left: pd.Series, right: pd.Series, operator: str) -> pd.Series:
        left_numeric = pd.to_numeric(left, errors="coerce")
        right_numeric = pd.to_numeric(right, errors="coerce")
        if operator == "gt":
            return left_numeric > right_numeric
        if operator == "gte":
            return left_numeric >= right_numeric
        if operator == "lt":
            return left_numeric < right_numeric
        if operator == "lte":
            return left_numeric <= right_numeric
        if operator == "eq":
            return left == right
        if operator == "ne":
            return left != right
        if operator == "crosses_above":
            return (left_numeric > right_numeric) & (left_numeric.shift(1) <= right_numeric.shift(1))
        if operator == "crosses_below":
            return (left_numeric < right_numeric) & (left_numeric.shift(1) >= right_numeric.shift(1))
        return pd.Series(False, index=left.index)

    def _evaluate_time_rule(self, comparison: pd.Series, time_rule: TimeRule) -> tuple[bool, dict[str, Any]]:
        series = comparison.fillna(False).astype(bool)
        if series.empty:
            return False, {"match_count": 0, "last_match_index": None, "last_match_offset": None}
        if time_rule.mode == "current":
            window = series.tail(1)
            matched = bool(window.iloc[-1])
        else:
            window = series.tail(time_rule.lookback)
            if time_rule.mode == "all":
                matched = len(window) >= time_rule.lookback and bool(window.all())
            else:
                matched = bool(window.any())
        match_points = list(window[window].index)
        last_match_index = match_points[-1] if match_points else None
        last_match_offset = None
        if last_match_index is not None:
            last_match_offset = len(window.index) - 1 - window.index.get_loc(last_match_index)
        return matched, {
            "match_count": len(match_points),
            "last_match_index": last_match_index,
            "last_match_offset": last_match_offset,
        }

    def _condition_score(
        self,
        *,
        matched: bool,
        operator: str,
        time_rule: TimeRule,
        match_left: Any,
        match_right: Any,
        timing: dict[str, Any],
    ) -> float:
        if not matched:
            return 0.0
        offset = timing.get("last_match_offset")
        if operator in {"crosses_above", "crosses_below"}:
            recency = 1.0
            if offset is not None and time_rule.lookback > 1:
                recency = max(0.0, 1 - offset / max(time_rule.lookback - 1, 1))
            return 75 + recency * 25
        left_number = self._to_number(match_left)
        right_number = self._to_number(match_right)
        if left_number is not None and right_number is not None:
            scale = max(abs(left_number), abs(right_number), 1.0)
            if operator in {"gt", "gte"}:
                margin = max(0.0, (left_number - right_number) / scale)
            elif operator in {"lt", "lte"}:
                margin = max(0.0, (right_number - left_number) / scale)
            elif operator == "eq":
                margin = max(0.0, 1 - abs(left_number - right_number) / scale)
            else:
                margin = 1.0
            score = 60 + min(40.0, margin * 120.0)
            if time_rule.mode == "any" and offset is not None:
                score -= min(15.0, offset * 5.0)
            return max(55.0, score)
        if isinstance(match_left, bool) or isinstance(match_right, bool):
            return 100.0
        return 80.0

    @staticmethod
    def _score_signal(score: float) -> str:
        if score >= 90:
            return "strong"
        if score >= 75:
            return "match"
        return "watch"

    @staticmethod
    def _to_number(value: Any) -> float | None:
        try:
            if value in (None, "", False, True):
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y%m%d")
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return round(value, 6)
        return value
