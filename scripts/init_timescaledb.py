import sys
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.database import sync_engine
from app.models.stock_model import Base, DailyBar


def table_exists(conn, table_name: str) -> bool:
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def init_timescaledb():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting database initialization...")

    with sync_engine.connect() as conn:
        print("Creating TimescaleDB extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        conn.commit()

        print("Creating all tables...")
        Base.metadata.create_all(conn)

        if table_exists(conn, "daily_bars"):
            print("Setting up TimescaleDB hypertable...")
            try:
                conn.execute(text("SELECT create_hypertable('daily_bars', 'trade_date');"))
                conn.commit()
                print("  - Created hypertable for daily_bars")
            except Exception as e:
                if "already a hypertable" in str(e):
                    print("  - daily_bars is already a hypertable")
                else:
                    print(f"  - Warning: {e}")

        print("Creating indexes...")
        indexes = [
            ("ix_daily_bars_ts_code_trade_date", "daily_bars", "ts_code, trade_date DESC"),
            ("ix_daily_bars_pct_chg", "daily_bars", "pct_chg DESC", "WHERE pct_chg IS NOT NULL"),
            ("ix_daily_bars_vol", "daily_bars", "vol DESC", "WHERE vol IS NOT NULL"),
            ("ix_stocks_ts_code", "stocks", "ts_code"),
            ("ix_stocks_symbol", "stocks", "symbol"),
            ("ix_stocks_name", "stocks", "name"),
            ("ix_fund_flows_ts_code", "fund_flows", "ts_code"),
            ("ix_fund_flows_trade_date", "fund_flows", "trade_date"),
            ("ix_daily_basic_ts_code", "daily_basic", "ts_code"),
            ("ix_daily_basic_trade_date", "daily_basic", "trade_date"),
            ("ix_indicators_ts_code", "indicators", "ts_code"),
            ("ix_indicators_trade_date", "indicators", "trade_date"),
            ("ix_patterns_ts_code", "patterns", "ts_code"),
            ("ix_patterns_trade_date", "patterns", "trade_date"),
        ]

        for idx_name, table_name, columns, *rest in indexes:
            where_clause = rest[0] if rest else ""
            if where_clause:
                sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns}) {where_clause};"
            else:
                sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns});"

            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  - Created index: {idx_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"  - Index already exists: {idx_name}")
                else:
                    print(f"  - Warning creating index {idx_name}: {e}")

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Database initialization completed!"
        )
        print("")


if __name__ == "__main__":
    init_timescaledb()
