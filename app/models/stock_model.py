from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), default="zh-CN")
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")
    extra: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="Tushare stock code"
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment="Stock symbol")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="Stock name")
    area: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Area")
    industry: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Industry")
    market: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Market type")
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, comment="Exchange")
    curr_type: Mapped[str] = mapped_column(String(10), default="CNY", comment="Currency type")
    list_status: Mapped[str] = mapped_column(String(5), default="L", comment="Listing status")
    list_date: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="Listing date")
    delist_date: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="Delisting date"
    )
    is_hs: Mapped[str | None] = mapped_column(String(5), nullable=True, comment="HS flag")
    is_etf: Mapped[bool] = mapped_column(Boolean, default=False, comment="Is ETF")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_stocks_ts_code", "ts_code"),
        Index("ix_stocks_symbol", "symbol"),
        Index("ix_stocks_name", "name"),
    )


class DailyBar(Base):
    __tablename__ = "daily_bars"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uq_daily_bars_ts_code_trade_date"),
        Index("ix_daily_bars_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), ForeignKey("stocks.ts_code"), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date | None] = mapped_column(Date, nullable=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    pre_close: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    change: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=True)
    pct_chg: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=True)
    vol: Mapped[Decimal] = mapped_column(Numeric(30, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(30, 2), nullable=False)
    adj_factor: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stock: Mapped["Stock"] = relationship("Stock", backref="daily_bars")


class FundFlow(Base):
    __tablename__ = "fund_flows"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uq_fund_flows_ts_code_trade_date"),
        Index("ix_fund_flows_ts_code", "ts_code"),
        Index("ix_fund_flows_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date | None] = mapped_column(Date, nullable=True)
    net_amount_main: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True)
    net_amount_hf: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True)
    net_amount_zz: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True)
    net_amount_dt: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True)
    net_amount_xd: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Attention(Base):
    __tablename__ = "attention"
    __table_args__ = (
        Index("ix_attention_user_id", "user_id"),
        UniqueConstraint("user_id", "ts_code", name="uq_attention_user_ts_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    group: Mapped[str] = mapped_column(String(50), default="watch", nullable=False, comment="Watchlist group: watch, observe, long-term")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="User notes for this stock")
    alert_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Alert thresholds: price_min, price_max, rsi_min, rsi_max")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint(
            "ts_code",
            "trade_date",
            "indicator_name",
            name="uq_indicators_ts_code_date_name",
        ),
        Index("ix_indicators_ts_code", "ts_code"),
        Index("ix_indicators_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date | None] = mapped_column(Date, nullable=True)
    indicator_name: Mapped[str] = mapped_column(String(50), nullable=False)
    indicator_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Pattern(Base):
    __tablename__ = "patterns"
    __table_args__ = (
        UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            "pattern_name",
            name="uq_patterns_ts_code_date_name",
        ),
        Index("ix_patterns_ts_code", "ts_code"),
        Index("ix_patterns_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[datetime] = mapped_column(Date, nullable=False)
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (
        Index("ix_strategies_user_id", "user_id"),
        UniqueConstraint("user_id", "name", name="uq_strategies_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 社交字段
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否公开到社区")
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, comment="官方认证策略")
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, comment="平均评分 0-5")
    rating_count: Mapped[int] = mapped_column(Integer, default=0, comment="评分人数")
    favorite_count: Mapped[int] = mapped_column(Integer, default=0, comment="收藏数")
    comment_count: Mapped[int] = mapped_column(Integer, default=0, comment="评论数")
    backtest_count: Mapped[int] = mapped_column(Integer, default=0, comment="被回测次数")
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="查看次数")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, comment="质量标签")
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="风险等级 low/medium/high")
    suitable_market: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="适用市场 bull/bear/sideway")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyResult(Base):
    __tablename__ = "strategy_results"
    __table_args__ = (
        Index("ix_strategy_results_ts_code", "ts_code"),
        Index("ix_strategy_results_strategy_id", "strategy_id"),
        Index("ix_strategy_results_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id"), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    signal: Mapped[str] = mapped_column(String(20), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    strategy: Mapped["Strategy"] = relationship("Strategy", backref="results")


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    __table_args__ = (Index("ix_backtest_results_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("strategies.id"), nullable=True
    )
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    final_capital: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=True)
    total_return: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    annual_return: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    sharpe_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SelectionCondition(Base):
    __tablename__ = "selection_conditions"
    __table_args__ = (Index("ix_selection_conditions_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SelectionResult(Base):
    __tablename__ = "selection_results"
    __table_args__ = (
        Index("ix_selection_results_selection_id", "selection_id"),
        Index("ix_selection_results_ts_code", "ts_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    selection_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockTop(Base):
    __tablename__ = "stock_tops"
    __table_args__ = (
        Index("ix_stock_tops_ts_code", "ts_code"),
        Index("ix_stock_tops_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ranking_times: Mapped[int] = mapped_column(Integer, default=0)
    sum_buy: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    sum_sell: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    buy_seat: Mapped[int] = mapped_column(Integer, default=0)
    sell_seat: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockBlockTrade(Base):
    __tablename__ = "stock_block_trades"
    __table_args__ = (
        Index("ix_stock_block_trades_ts_code", "ts_code"),
        Index("ix_stock_block_trades_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    pct_chg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    premium_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    total_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockBonus(Base):
    __tablename__ = "stock_bonus"
    __table_args__ = (
        Index("ix_stock_bonus_ts_code", "ts_code"),
        Index("ix_stock_bonus_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bonus_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bonus_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    transfer_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    cash_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    div_yield: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    record_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ex_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockLimitupReason(Base):
    __tablename__ = "stock_limitup_reasons"
    __table_args__ = (
        Index("ix_stock_limitup_reasons_ts_code", "ts_code"),
        Index("ix_stock_limitup_reasons_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    pct_chg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    limitup_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_limitup_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    limitup_count: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockChipRace(Base):
    __tablename__ = "stock_chip_races"
    __table_args__ = (
        Index("ix_stock_chip_races_ts_code", "ts_code"),
        Index("ix_stock_chip_races_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    race_type: Mapped[str] = mapped_column(String(20), nullable=False)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    pct_chg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    turnover_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    net_inflow: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SectorFundFlow(Base):
    __tablename__ = "sector_fund_flows"
    __table_args__ = (
        Index("ix_sector_fund_flows_sector_name", "sector_name"),
        Index("ix_sector_fund_flows_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sector_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    pct_chg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    net_amount_main: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    net_rate_main: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    net_amount_hf: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    net_rate_hf: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    top_stock: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NorthBoundFund(Base):
    __tablename__ = "north_bound_funds"
    __table_args__ = (
        Index("ix_north_bound_funds_ts_code", "ts_code"),
        Index("ix_north_bound_funds_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    close: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    pct_chg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sh_net_inflow: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    sz_net_inflow: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    total_net_inflow: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BacktestTask(Base):
    __tablename__ = "backtest_tasks"
    __table_args__ = (Index("ix_backtest_tasks_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    backtest_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
