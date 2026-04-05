"""
Migrate data from MySQL to PostgreSQL/TimescaleDB.
This script requires the original MySQL database and the new PostgreSQL database.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional
import yaml

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.stock_model import (
    Stock,
    DailyBar,
    FundFlow,
    Indicator,
    Pattern,
    Strategy,
    StrategyResult,
)
from app.config import settings


def load_config():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_db_config(config):
    # Support both the legacy `mysql` key and the current `database` key.
    db_config = config.get("mysql") or config.get("database")
    if not db_config:
        raise KeyError("config.yaml must define either a `mysql` or `database` section")
    return db_config


def _get_env_or_config(env_key: str, config_value, default=None):
    value = os.getenv(env_key)
    if value not in (None, ""):
        return value
    if config_value not in (None, ""):
        return config_value
    return default


def get_mysql_connection(config):
    db_config = _get_db_config(config)
    return pymysql.connect(
        host=_get_env_or_config("MYSQL_HOST", db_config.get("host"), "localhost"),
        port=int(_get_env_or_config("MYSQL_PORT", db_config.get("port"), 3306)),
        user=_get_env_or_config("MYSQL_USER", db_config.get("user")),
        password=_get_env_or_config("MYSQL_PASSWORD", db_config.get("password")),
        database=_get_env_or_config("MYSQL_DATABASE", db_config.get("database")),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def migrate_stocks(mysql_conn, pg_session: Session):
    print("Migrating stocks...")
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT * FROM stock_basic")
        stocks = cursor.fetchall()

        for stock in stocks:
            existing = (
                pg_session.query(Stock)
                .filter(Stock.ts_code == stock["ts_code"])
                .first()
            )
            if not existing:
                pg_stock = Stock(
                    ts_code=stock["ts_code"],
                    symbol=stock["symbol"],
                    name=stock["name"],
                    area=stock.get("area"),
                    industry=stock.get("industry"),
                    market=stock.get("market"),
                    exchange=stock.get("exchange", ""),
                    curr_type=stock.get("curr_type", "CNY"),
                    list_status=stock.get("list_status", "L"),
                    list_date=stock.get("list_date"),
                    delist_date=stock.get("delist_date"),
                    is_hs=stock.get("is_hs"),
                    is_etf=stock.get("is_etf", False),
                )
                pg_session.add(pg_stock)
        pg_session.commit()
    print(f"Migrated {len(stocks)} stocks")


def migrate_daily_bars(mysql_conn, pg_session: Session, batch_size: int = 10000):
    print("Migrating daily bars...")
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM daily_basic")
        total = cursor.fetchone()["COUNT(*)"]

        offset = 0
        while offset < total:
            cursor.execute(
                f"SELECT * FROM daily_basic LIMIT {batch_size} OFFSET {offset}"
            )
            bars = cursor.fetchall()

            for bar in bars:
                existing = (
                    pg_session.query(DailyBar)
                    .filter(
                        DailyBar.ts_code == bar["ts_code"],
                        DailyBar.trade_date == bar["trade_date"],
                    )
                    .first()
                )
                if not existing:
                    pg_bar = DailyBar(
                        ts_code=bar["ts_code"],
                        trade_date=bar["trade_date"],
                        open=Decimal(str(bar.get("open", 0))),
                        high=Decimal(str(bar.get("high", 0))),
                        low=Decimal(str(bar.get("low", 0))),
                        close=Decimal(str(bar.get("close", 0))),
                        pre_close=Decimal(str(bar.get("pre_close", 0))),
                        change=Decimal(str(bar.get("change", 0)))
                        if bar.get("change")
                        else None,
                        pct_chg=Decimal(str(bar.get("pct_chg", 0)))
                        if bar.get("pct_chg")
                        else None,
                        vol=Decimal(str(bar.get("vol", 0))),
                        amount=Decimal(str(bar.get("amount", 0))),
                        adj_factor=Decimal(str(bar.get("adj_factor", 0)))
                        if bar.get("adj_factor")
                        else None,
                    )
                    pg_session.add(pg_bar)

            pg_session.commit()
            offset += batch_size
            print(f"  Migrated {min(offset, total)}/{total} bars")

    print("Daily bars migration completed")


def migrate_fund_flows(mysql_conn, pg_session: Session, batch_size: int = 10000):
    print("Migrating fund flows...")
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM fund_flow")
        total = cursor.fetchone()["COUNT(*)"]

        offset = 0
        while offset < total:
            cursor.execute(
                f"SELECT * FROM fund_flow LIMIT {batch_size} OFFSET {offset}"
            )
            flows = cursor.fetchall()

            for flow in flows:
                existing = (
                    pg_session.query(FundFlow)
                    .filter(
                        FundFlow.ts_code == flow["ts_code"],
                        FundFlow.trade_date == flow["trade_date"],
                    )
                    .first()
                )
                if not existing:
                    pg_flow = FundFlow(
                        ts_code=flow["ts_code"],
                        trade_date=flow["trade_date"],
                        net_amount_main=Decimal(str(flow.get("net_amount_main", 0)))
                        if flow.get("net_amount_main")
                        else None,
                        net_amount_hf=Decimal(str(flow.get("net_amount_hf", 0)))
                        if flow.get("net_amount_hf")
                        else None,
                        net_amount_zz=Decimal(str(flow.get("net_amount_zz", 0)))
                        if flow.get("net_amount_zz")
                        else None,
                        net_amount_dt=Decimal(str(flow.get("net_amount_dt", 0)))
                        if flow.get("net_amount_dt")
                        else None,
                        net_amount_xd=Decimal(str(flow.get("net_amount_xd", 0)))
                        if flow.get("net_amount_xd")
                        else None,
                    )
                    pg_session.add(pg_flow)

            pg_session.commit()
            offset += batch_size
            print(f"  Migrated {min(offset, total)}/{total} fund flows")

    print("Fund flows migration completed")


def run_migration():
    config = load_config()

    mysql_conn = get_mysql_connection(config)

    pg_engine = create_engine(str(settings.SYNC_DATABASE_URL))
    PgSessionLocal = sessionmaker(bind=pg_engine)
    pg_session = PgSessionLocal()

    try:
        migrate_stocks(mysql_conn, pg_session)
        migrate_daily_bars(mysql_conn, pg_session)
        migrate_fund_flows(mysql_conn, pg_session)
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        pg_session.rollback()
        raise
    finally:
        mysql_conn.close()
        pg_session.close()
        pg_engine.dispose()


if __name__ == "__main__":
    run_migration()
