from typing import Any

from sqlalchemy import text

from app.schemas.selection_schema import ScreeningScope, SelectionFilters

CANONICAL_BACKTEST_KEYS = (
    "strategy_type",
    "stock_code",
    "period",
    "initial_capital",
    "position_size",
    "max_position",
    "stop_loss",
    "take_profit",
    "min_hold_days",
    "commission_rate",
    "min_commission",
    "slippage",
)

CANONICAL_SELECTION_KEYS = (
    "selection_filters",
    "selection_scope",
    "entry_rules",
    "exit_rules",
)


def _dump_model_or_dict(value: object, *, by_alias: bool = True) -> dict:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=by_alias, exclude_none=True)
    if isinstance(value, dict):
        return {key: item for key, item in value.items() if item is not None}
    return {}


def _dump_nested_payload(value: object) -> dict:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {
            key: (
                _dump_nested_payload(item)
                if isinstance(item, dict) or hasattr(item, "model_dump")
                else item
            )
            for key, item in value.items()
            if item is not None
        }
    return {}


def _normalize_strategy_source(raw_params: dict[str, Any], backtest_config: dict[str, Any]) -> str:
    source = str(raw_params.get("source") or "").strip()
    if source:
        return source
    if (
        raw_params.get("selection_filters") is not None
        or raw_params.get("selection_scope") is not None
    ):
        return "selection"
    if backtest_config:
        return "backtest"
    return "manual"


def _normalize_strategy_template_name(
    raw_params: dict[str, Any], backtest_config: dict[str, Any]
) -> str:
    template_name = str(raw_params.get("template_name") or "").strip()
    if template_name:
        return template_name

    strategy_type = str(
        backtest_config.get("strategy_type") or raw_params.get("strategy_type") or ""
    ).strip()
    if strategy_type:
        return strategy_type

    nested_strategy = raw_params.get("strategy")
    if isinstance(nested_strategy, dict):
        nested_template = str(
            nested_strategy.get("template_name")
            or nested_strategy.get("strategy_type")
            or nested_strategy.get("template")
            or nested_strategy.get("name")
            or ""
        ).strip()
        if nested_template:
            return nested_template

    return (
        "selection_bridge"
        if _normalize_strategy_source(raw_params, backtest_config) == "selection"
        else "manual"
    )


def _normalize_backtest_config(raw_params: dict[str, Any]) -> dict[str, Any]:
    backtest_config = {}
    nested_backtest_config = raw_params.get("backtest_config")
    if isinstance(nested_backtest_config, dict) or hasattr(nested_backtest_config, "model_dump"):
        backtest_config.update(_dump_model_or_dict(nested_backtest_config, by_alias=True))

    for key in CANONICAL_BACKTEST_KEYS:
        value = raw_params.get(key)
        if value is not None:
            backtest_config[key] = value

    nested_strategy = raw_params.get("strategy")
    if isinstance(nested_strategy, dict):
        nested_strategy_params = nested_strategy.get("params")
        if isinstance(nested_strategy_params, dict) or hasattr(
            nested_strategy_params, "model_dump"
        ):
            nested_strategy_params = _dump_model_or_dict(nested_strategy_params, by_alias=True)
            for key in CANONICAL_BACKTEST_KEYS:
                if key not in backtest_config and nested_strategy_params.get(key) is not None:
                    backtest_config[key] = nested_strategy_params[key]

    return backtest_config


def _build_selection_entry_rules(
    selection_filters: dict[str, Any], selection_scope: dict[str, Any]
) -> dict[str, Any]:
    return {
        "mode": "screening_match",
        "inherits": ["selection_filters", "selection_scope"],
        "filters": selection_filters,
        "scope": selection_scope,
    }


def _build_template_entry_rules(
    template_name: str, strategy_params: dict[str, Any]
) -> dict[str, Any]:
    return {
        "mode": "template_signal",
        "template_name": template_name,
        "strategy_params": strategy_params,
    }


def _build_exit_rules(
    *,
    source: str,
    backtest_config: dict[str, Any],
) -> dict[str, Any]:
    stop_loss = backtest_config.get("stop_loss")
    take_profit = backtest_config.get("take_profit")
    max_hold_days = backtest_config.get("min_hold_days") or backtest_config.get("max_hold_days")

    if source == "selection":
        return {
            "mode": "configurable",
            "rules": [
                {"name": "take_profit_pct", "label": "止盈百分比", "type": "number"},
                {"name": "stop_loss_pct", "label": "止损百分比", "type": "number"},
                {"name": "max_hold_days", "label": "最大持有天数", "type": "number"},
            ],
        }

    return {
        "mode": "fixed_risk",
        "stop_loss_pct": stop_loss,
        "take_profit_pct": take_profit,
        "max_hold_days": max_hold_days,
    }


def _normalize_strategy_params(
    raw_params: object | None, *, default_source: str | None = None
) -> dict[str, Any] | None:
    if not isinstance(raw_params, dict) and not hasattr(raw_params, "model_dump"):
        return raw_params

    params = _dump_model_or_dict(raw_params, by_alias=True)
    if not params:
        source = default_source or "manual"
        template_name = "selection_bridge" if source == "selection" else "manual"
        return {
            "source": source,
            "template_name": template_name,
            "selection_filters": {},
            "selection_scope": {},
            "entry_rules": {},
            "exit_rules": {},
            "backtest_config": {},
            "strategy_params": {},
        }

    selection_filters = _dump_model_or_dict(params.get("selection_filters"), by_alias=True)
    selection_scope = _dump_model_or_dict(params.get("selection_scope"), by_alias=True)
    entry_rules = _dump_nested_payload(params.get("entry_rules"))
    exit_rules = _dump_nested_payload(params.get("exit_rules"))
    backtest_config = _normalize_backtest_config(params)

    source = default_source or _normalize_strategy_source(params, backtest_config)
    template_name = _normalize_strategy_template_name(params, backtest_config)
    strategy_params = _dump_nested_payload(params.get("strategy_params"))

    if not strategy_params and isinstance(params.get("strategy"), dict):
        nested_strategy = params["strategy"]
        nested_params = nested_strategy.get("params")
        if isinstance(nested_params, dict) or hasattr(nested_params, "model_dump"):
            strategy_params = _dump_model_or_dict(nested_params, by_alias=True)

    if not selection_filters and params.get("filters") is not None:
        selection_filters = _dump_model_or_dict(params.get("filters"), by_alias=True)
    if not selection_scope and params.get("scope") is not None:
        selection_scope = _dump_model_or_dict(params.get("scope"), by_alias=True)

    if not entry_rules:
        if source == "selection":
            entry_rules = _build_selection_entry_rules(selection_filters, selection_scope)
        else:
            entry_rules = _build_template_entry_rules(template_name, strategy_params)
    if not exit_rules:
        exit_rules = _build_exit_rules(source=source, backtest_config=backtest_config)

    canonical_params: dict[str, Any] = {
        "source": source,
        "template_name": template_name,
        "selection_filters": selection_filters,
        "selection_scope": selection_scope,
        "entry_rules": entry_rules,
        "exit_rules": exit_rules,
        "backtest_config": backtest_config,
        "strategy_params": strategy_params,
    }

    return canonical_params


def _selection_strategy_template() -> dict:
    return {
        "name": "selection_bridge",
        "display_name": "筛选转策略",
        "description": "将当前筛选条件保存为可回测策略，入场条件继承筛选条件，出场条件可单独配置。",
        "source": "selection",
        "default_params": {
            "source": "selection",
            "template_name": "selection_bridge",
            "selection_filters": {},
            "selection_scope": {},
            "entry_rules": {
                "mode": "screening_match",
                "inherits": ["selection_filters", "selection_scope"],
            },
            "exit_rules": {
                "mode": "configurable",
                "rules": [
                    {"name": "take_profit_pct", "label": "止盈百分比", "type": "number"},
                    {"name": "stop_loss_pct", "label": "止损百分比", "type": "number"},
                    {"name": "max_hold_days", "label": "最大持有天数", "type": "number"},
                ],
            },
            "backtest_config": {},
            "strategy_params": {},
        },
        "selection_schema": {
            "filters": SelectionFilters.model_json_schema(),
            "scope": ScreeningScope.model_json_schema(),
        },
        "entry_rules_template": {
            "mode": "screening_match",
            "inherits": ["selection_filters", "selection_scope"],
        },
        "exit_rules_template": {
            "mode": "configurable",
            "rules": [
                {"name": "take_profit_pct", "label": "止盈百分比", "type": "number"},
                {"name": "stop_loss_pct", "label": "止损百分比", "type": "number"},
                {"name": "max_hold_days", "label": "最大持有天数", "type": "number"},
            ],
        },
        "parameters": [
            {
                "name": "exit_mode",
                "label": "出场模式",
                "type": "select",
                "default": "configurable",
                "options": [
                    {"label": "可配置", "value": "configurable"},
                    {"label": "跟随筛选结果", "value": "inherit_selection"},
                ],
            }
        ],
    }


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

STRATEGY_TEMPLATES = [
    {
        "name": "ma_crossover",
        "display_name": "MA 交叉",
        "description": "短期均线上穿长期均线时生成买入信号。",
        "default_params": {"fast_ma": 5, "slow_ma": 20},
        "parameters": [
            {
                "name": "fast_ma",
                "label": "快速 MA",
                "type": "number",
                "default": 5,
                "min": 2,
                "max": 60,
                "step": 1,
            },
            {
                "name": "slow_ma",
                "label": "慢速 MA",
                "type": "number",
                "default": 20,
                "min": 5,
                "max": 250,
                "step": 1,
            },
        ],
    },
    {
        "name": "rsi_oversold",
        "display_name": "RSI 超卖",
        "description": "RSI 跌入超卖区间后等待均值回归。",
        "default_params": {"rsi_period": 14, "oversold_level": 30},
        "parameters": [
            {
                "name": "rsi_period",
                "label": "RSI 周期",
                "type": "number",
                "default": 14,
                "min": 2,
                "max": 60,
                "step": 1,
            },
            {
                "name": "oversold_level",
                "label": "超卖水平",
                "type": "number",
                "default": 30,
                "min": 5,
                "max": 50,
                "step": 1,
            },
        ],
    },
    {
        "name": "macd_cross",
        "display_name": "MACD 交叉",
        "description": "MACD 快慢线金叉时触发入场。",
        "default_params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "parameters": [
            {
                "name": "fast_period",
                "label": "快线周期",
                "type": "number",
                "default": 12,
                "min": 2,
                "max": 30,
                "step": 1,
            },
            {
                "name": "slow_period",
                "label": "慢线周期",
                "type": "number",
                "default": 26,
                "min": 5,
                "max": 60,
                "step": 1,
            },
            {
                "name": "signal_period",
                "label": "信号周期",
                "type": "number",
                "default": 9,
                "min": 2,
                "max": 30,
                "step": 1,
            },
        ],
    },
    {
        "name": "boll_breakout",
        "display_name": "布林带突破",
        "description": "价格突破布林带时跟随趋势。",
        "default_params": {"boll_period": 20, "boll_std": 2, "breakout_mode": "upper"},
        "parameters": [
            {
                "name": "boll_period",
                "label": "布林周期",
                "type": "number",
                "default": 20,
                "min": 5,
                "max": 60,
                "step": 1,
            },
            {
                "name": "boll_std",
                "label": "标准差",
                "type": "number",
                "default": 2,
                "min": 1,
                "max": 4,
                "step": 0.1,
            },
            {
                "name": "breakout_mode",
                "label": "突破方向",
                "type": "select",
                "default": "upper",
                "options": [
                    {"label": "上轨突破", "value": "upper"},
                    {"label": "下轨反转", "value": "lower"},
                    {"label": "双向", "value": "both"},
                ],
            },
        ],
    },
    {
        "name": "pattern_based",
        "display_name": "形态策略",
        "description": "基于已识别形态触发回测入场条件。",
        "default_params": {"pattern_name": "HAMMER", "confirmation_bars": 2},
        "parameters": [
            {
                "name": "pattern_name",
                "label": "形态名称",
                "type": "select",
                "default": "HAMMER",
                "options": [
                    {"label": "锤头线", "value": "HAMMER"},
                    {"label": "十字星", "value": "DOJI"},
                    {"label": "看涨吞没", "value": "BULLISH_ENGULFING"},
                ],
            },
            {
                "name": "confirmation_bars",
                "label": "确认K线数",
                "type": "number",
                "default": 2,
                "min": 1,
                "max": 10,
                "step": 1,
            },
        ],
    },
    _selection_strategy_template(),
]


class StrategyService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def get_strategy_list() -> list[dict]:
        return STRATEGIES

    @staticmethod
    def get_strategy_templates() -> list[dict]:
        return STRATEGY_TEMPLATES

    @staticmethod
    def build_selection_strategy_params(
        selection_filters: object | None,
        selection_scope: object | None = None,
        entry_rules: dict | None = None,
        exit_rules: dict | None = None,
        template_name: str = "selection_bridge",
        extra_params: dict | None = None,
    ) -> dict:
        params = {
            "source": "selection",
            "template_name": template_name,
            "selection_filters": _dump_model_or_dict(selection_filters, by_alias=True),
            "selection_scope": _dump_model_or_dict(selection_scope, by_alias=True),
            "entry_rules": entry_rules
            or _build_selection_entry_rules(
                _dump_model_or_dict(selection_filters, by_alias=True),
                _dump_model_or_dict(selection_scope, by_alias=True),
            ),
            "exit_rules": exit_rules or _build_exit_rules(source="selection", backtest_config={}),
            "backtest_config": {},
            "strategy_params": {},
        }
        if extra_params:
            params.update({key: value for key, value in extra_params.items() if value is not None})
        return params

    @staticmethod
    def build_strategy_params(
        params: object | None, default_source: str | None = None
    ) -> dict[str, Any] | None:
        return _normalize_strategy_params(params, default_source=default_source)

    async def run_strategy(self, strategy_name: str, date: str | None):
        return {"status": "success", "strategy": strategy_name, "count": 0}

    async def get_results(
        self, strategy_name: str | None = None, date: str | None = None, limit: int = 100
    ):
        where_clauses = []
        params = {"limit": limit}

        if strategy_name:
            where_clauses.append("st.name = :strategy_name")
            params["strategy_name"] = strategy_name
        if date:
            where_clauses.append("sr.trade_date = :trade_date")
            params["trade_date"] = date

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = text(f"""
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
            {where_sql}
            ORDER BY sr.score DESC, sr.trade_date DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, params)
        return [dict(row._mapping) for row in result.fetchall()]
