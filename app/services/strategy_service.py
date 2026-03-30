from sqlalchemy import text

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
