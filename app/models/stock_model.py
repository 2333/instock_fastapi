from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    CheckConstraint,
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


class UserEvent(Base):
    __tablename__ = "user_events"
    __table_args__ = (
        Index("ix_user_events_user_created", "user_id", "created_at"),
        Index("ix_user_events_event_type_created", "event_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    page: Mapped[str] = mapped_column(String(120), nullable=False)
    referrer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


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
    industry_label: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Industry label from BaoStock")
    industry_taxonomy: Mapped[str | None] = mapped_column(
        String(80), nullable=True, comment="Industry taxonomy from BaoStock"
    )
    industry_source: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Industry source")
    industry_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Industry refresh time")
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
        UniqueConstraint("ts_code", "trade_date_dt", name="uq_daily_bars_ts_code_trade_date_dt"),
        Index("ix_daily_bars_trade_date", "trade_date"),
        Index("ix_daily_bars_trade_date_dt", "trade_date_dt"),
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
    source: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Data source")
    adj_factor: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stock: Mapped["Stock"] = relationship("Stock", backref="daily_bars")


class FundFlow(Base):
    __tablename__ = "fund_flows"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date_dt", name="uq_fund_flows_ts_code_trade_date_dt"),
        Index("ix_fund_flows_ts_code", "ts_code"),
        Index("ix_fund_flows_trade_date", "trade_date"),
        Index("ix_fund_flows_trade_date_dt", "trade_date_dt"),
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


class AlertCondition(Base):
    __tablename__ = "alert_conditions"
    __table_args__ = (
        Index("ix_alert_conditions_user_id", "user_id"),
        Index("ix_alert_conditions_ts_code", "ts_code"),
        UniqueConstraint(
            "user_id",
            "ts_code",
            "rule_type",
            "threshold",
            name="uq_alert_conditions_user_ts_code_rule_type_threshold",
        ),
        CheckConstraint(
            "rule_type IN ('price_above', 'price_below', 'change_above', 'change_below')",
            name="ck_alert_conditions_rule_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_alert_condition_id", "alert_condition_id"),
        Index("ix_notifications_subscription_id", "subscription_id"),
        Index("ix_notifications_alert_run_id", "alert_run_id"),
        Index("uq_notifications_dedupe_key", "dedupe_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    alert_condition_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("alert_conditions.id"), nullable=True
    )
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alert_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notification_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            "indicator_name",
            name="uq_indicators_ts_code_trade_date_dt_name",
        ),
        Index("ix_indicators_ts_code", "ts_code"),
        Index("ix_indicators_trade_date", "trade_date"),
        Index("ix_indicators_trade_date_dt", "trade_date_dt"),
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
        Index("ix_patterns_trade_date_dt", "trade_date_dt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date] = mapped_column(Date, nullable=False)
    pattern_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(20), nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyBasic(Base):
    __tablename__ = "daily_basic"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date_dt", name="uq_daily_basic_ts_code_trade_date_dt"),
        Index("ix_daily_basic_ts_code", "ts_code"),
        Index("ix_daily_basic_trade_date", "trade_date"),
        Index("ix_daily_basic_trade_date_dt", "trade_date_dt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date] = mapped_column(Date, nullable=False)
    turnover_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    turnover_rate_f: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    volume_ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    pe: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    pe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    pb: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ps: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ps_ttm: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    dv_ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    dv_ttm: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    total_share: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    float_share: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    free_share: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    total_mv: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    circ_mv: Mapped[Decimal | None] = mapped_column(Numeric(30, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockST(Base):
    __tablename__ = "stock_st"
    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date_dt", name="uq_stock_st_ts_code_trade_date_dt"),
        Index("ix_stock_st_ts_code", "ts_code"),
        Index("ix_stock_st_trade_date", "trade_date"),
        Index("ix_stock_st_trade_date_dt", "trade_date_dt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    st_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    begin_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TechnicalFactor(Base):
    __tablename__ = "technical_factors"
    __table_args__ = (
        UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            name="uq_technical_factors_ts_code_trade_date_dt",
        ),
        Index("ix_technical_factors_ts_code", "ts_code"),
        Index("ix_technical_factors_trade_date", "trade_date"),
        Index("ix_technical_factors_trade_date_dt", "trade_date_dt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    trade_date_dt: Mapped[date] = mapped_column(Date, nullable=False)
    factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    definition_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"
    __table_args__ = (
        Index("ix_alert_subscriptions_user_id", "user_id"),
        Index("ix_alert_subscriptions_selection_condition_id", "selection_condition_id"),
        Index("ix_alert_subscriptions_status", "status"),
        UniqueConstraint(
            "user_id",
            "selection_condition_id",
            "definition_hash",
            "schedule_type",
            name="uq_alert_subscriptions_user_condition_hash_schedule",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_condition_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False, default="post_close")
    cooldown_trade_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_run_trade_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_notified_trade_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlertRun(Base):
    __tablename__ = "alert_runs"
    __table_args__ = (
        Index("ix_alert_runs_subscription_id", "subscription_id"),
        Index("ix_alert_runs_trade_date", "trade_date"),
        Index("ix_alert_runs_user_id", "user_id"),
        UniqueConstraint(
            "subscription_id",
            "trade_date",
            "definition_hash",
            name="uq_alert_runs_subscription_trade_date_definition_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_condition_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    definition_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notification_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AlertRunHit(Base):
    __tablename__ = "alert_run_hits"
    __table_args__ = (
        Index("ix_alert_run_hits_run_id", "run_id"),
        Index("ix_alert_run_hits_ts_code", "ts_code"),
        UniqueConstraint("run_id", "ts_code", name="uq_alert_run_hits_run_ts_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ts_code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    signal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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


class ParameterOptimizationJob(Base):
    __tablename__ = "parameter_optimization_jobs"
    __table_args__ = (
        Index("ix_parameter_optimization_jobs_user_created", "user_id", "created_at"),
        Index("ix_parameter_optimization_jobs_status", "status"),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_parameter_optimization_jobs_status",
        ),
        CheckConstraint(
            "method IN ('random_search')",
            name="ck_parameter_optimization_jobs_method",
        ),
        CheckConstraint(
            "objective_direction IN ('maximize', 'minimize')",
            name="ck_parameter_optimization_jobs_objective_direction",
        ),
        CheckConstraint(
            "objective_metric IN ('sharpe_ratio', 'total_return', 'max_drawdown')",
            name="ck_parameter_optimization_jobs_objective_metric",
        ),
        CheckConstraint("trial_count >= 1 AND trial_count <= 50", name="ck_parameter_optimization_jobs_trial_count"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    method: Mapped[str] = mapped_column(String(30), nullable=False, default="random_search")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    base_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parameter_space: Mapped[dict] = mapped_column(JSONB, nullable=False)
    objective_metric: Mapped[str] = mapped_column(String(40), nullable=False)
    objective_direction: Mapped[str] = mapped_column(String(10), nullable=False, default="maximize")
    trial_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_trials: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_trials: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_trial_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    best_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    trials: Mapped[list["ParameterOptimizationTrial"]] = relationship(
        "ParameterOptimizationTrial",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ParameterOptimizationTrial(Base):
    __tablename__ = "parameter_optimization_trials"
    __table_args__ = (
        UniqueConstraint("job_id", "trial_index", name="uq_parameter_optimization_trials_job_index"),
        Index("ix_parameter_optimization_trials_job_id", "job_id"),
        Index("ix_parameter_optimization_trials_status", "status"),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_parameter_optimization_trials_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("parameter_optimization_jobs.id"), nullable=False)
    trial_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    job: Mapped["ParameterOptimizationJob"] = relationship(
        "ParameterOptimizationJob",
        back_populates="trials",
    )
