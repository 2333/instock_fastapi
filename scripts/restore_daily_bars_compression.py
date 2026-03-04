#!/usr/bin/env python3
from sqlalchemy import text
from app.database import sync_engine


def main() -> None:
    with sync_engine.connect() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE daily_bars SET (
                    timescaledb.compress = true,
                    timescaledb.compress_segmentby = 'ts_code'
                );
                """
            )
        )
        conn.execute(
            text(
                """
                SELECT add_compression_policy(
                    'daily_bars',
                    INTERVAL '90 days',
                    if_not_exists => true
                );
                """
            )
        )
        conn.commit()
        print("daily_bars 压缩与压缩策略已恢复")


if __name__ == "__main__":
    main()
