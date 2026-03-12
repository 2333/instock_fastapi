import os
from collections.abc import Iterable
from urllib.parse import urlparse

import psycopg2


TS_CODE_TABLES = (
    "stocks",
    "daily_bars",
    "fund_flows",
    "attention",
    "indicators",
    "patterns",
    "strategy_results",
    "selection_results",
    "stock_tops",
    "stock_block_trades",
    "stock_bonus",
    "stock_limitup_reasons",
    "stock_chip_races",
    "north_bound_funds",
    "backfill_daily_state",
)


NORMALIZE_TS_CODE_SQL = """
CASE
  WHEN ts_code IS NULL OR ts_code = '' THEN ts_code
  WHEN split_part(ts_code, '.', 2) = 'SH' THEN split_part(ts_code, '.', 1) || '.SH'
  WHEN split_part(ts_code, '.', 2) = 'SZ' THEN split_part(ts_code, '.', 1) || '.SZ'
  WHEN split_part(ts_code, '.', 2) = 'BJ' THEN split_part(ts_code, '.', 1) || '.BJ'
  WHEN split_part(ts_code, '.', 2) = 'SSE' THEN split_part(ts_code, '.', 1) || '.SH'
  WHEN split_part(ts_code, '.', 2) = 'SZSE' THEN split_part(ts_code, '.', 1) || '.SZ'
  WHEN split_part(ts_code, '.', 2) = 'BSE' THEN split_part(ts_code, '.', 1) || '.BJ'
  WHEN split_part(ts_code, '.', 2) = 'UNKNOWN' THEN
    CASE
      WHEN split_part(ts_code, '.', 1) ~ '^[65]' THEN split_part(ts_code, '.', 1) || '.SH'
      WHEN split_part(ts_code, '.', 1) ~ '^[0123]' THEN split_part(ts_code, '.', 1) || '.SZ'
      WHEN split_part(ts_code, '.', 1) ~ '^[489]' THEN split_part(ts_code, '.', 1) || '.BJ'
      ELSE split_part(ts_code, '.', 1)
    END
  WHEN position('.' in ts_code) = 0 THEN
    CASE
      WHEN ts_code ~ '^[65]' THEN ts_code || '.SH'
      WHEN ts_code ~ '^[0123]' THEN ts_code || '.SZ'
      WHEN ts_code ~ '^[489]' THEN ts_code || '.BJ'
      ELSE ts_code
    END
  ELSE ts_code
END
"""


NORMALIZE_AUDIT_KEY_SQL = """
CASE
  WHEN entity_key IS NULL OR entity_key = '' THEN entity_key
  WHEN entity_key !~ '^[0-9A-Z]+\\.' THEN entity_key
  WHEN split_part(entity_key, '.', 2) = 'SH' THEN split_part(entity_key, '.', 1) || '.SH'
  WHEN split_part(entity_key, '.', 2) = 'SZ' THEN split_part(entity_key, '.', 1) || '.SZ'
  WHEN split_part(entity_key, '.', 2) = 'BJ' THEN split_part(entity_key, '.', 1) || '.BJ'
  WHEN split_part(entity_key, '.', 2) = 'SSE' THEN split_part(entity_key, '.', 1) || '.SH'
  WHEN split_part(entity_key, '.', 2) = 'SZSE' THEN split_part(entity_key, '.', 1) || '.SZ'
  WHEN split_part(entity_key, '.', 2) = 'BSE' THEN split_part(entity_key, '.', 1) || '.BJ'
  WHEN split_part(entity_key, '.', 2) = 'UNKNOWN' THEN
    CASE
      WHEN split_part(entity_key, '.', 1) ~ '^[65]' THEN split_part(entity_key, '.', 1) || '.SH'
      WHEN split_part(entity_key, '.', 1) ~ '^[0123]' THEN split_part(entity_key, '.', 1) || '.SZ'
      WHEN split_part(entity_key, '.', 1) ~ '^[489]' THEN split_part(entity_key, '.', 1) || '.BJ'
      ELSE split_part(entity_key, '.', 1)
    END
  ELSE entity_key
END
"""


NORMALIZE_EXCHANGE_SQL = """
CASE
  WHEN exchange IS NULL OR exchange = '' THEN exchange
  WHEN upper(exchange) IN ('SH', 'SSE') THEN 'SH'
  WHEN upper(exchange) IN ('SZ', 'SZSE') THEN 'SZ'
  WHEN upper(exchange) IN ('BJ', 'BSE') THEN 'BJ'
  WHEN upper(exchange) = 'UNKNOWN' THEN
    CASE
      WHEN symbol ~ '^[65]' THEN 'SH'
      WHEN symbol ~ '^[0123]' THEN 'SZ'
      WHEN symbol ~ '^[489]' THEN 'BJ'
      ELSE 'UNKNOWN'
    END
  ELSE upper(exchange)
END
"""


def build_dsn() -> str:
    explicit = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit:
        return explicit.replace("+psycopg2", "").replace("+asyncpg", "")

    user = os.getenv("POSTGRES_USER", "instock")
    password = os.getenv("POSTGRES_PASSWORD", "instock")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "instock")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def print_counts(cur, title: str, sql: str) -> None:
    print(title)
    cur.execute(sql)
    for row in cur.fetchall():
        print("  ", row)


def execute_many(cur, statements: Iterable[str]) -> None:
    for statement in statements:
        cur.execute(statement)


def main() -> None:
    dsn = build_dsn()
    parsed = urlparse(dsn)
    print(f"connecting: {parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}")

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            print_counts(
                cur,
                "before stocks suffix:",
                "select split_part(ts_code, '.', 2) as suffix, count(*) from stocks group by 1 order by 2 desc",
            )
            print_counts(
                cur,
                "before stocks exchange:",
                "select exchange, count(*) from stocks group by 1 order by 2 desc",
            )

            cur.execute("SET session_replication_role = replica")

            execute_many(
                cur,
                [
                    f"UPDATE {table} SET ts_code = {NORMALIZE_TS_CODE_SQL} WHERE ts_code IS NOT NULL"
                    for table in TS_CODE_TABLES
                ],
            )

            cur.execute(
                f"""
                UPDATE data_fetch_audit
                SET entity_key = {NORMALIZE_AUDIT_KEY_SQL}
                WHERE entity_key IS NOT NULL
                  AND entity_key <> ''
                """
            )

            cur.execute(
                f"""
                UPDATE stocks
                SET exchange = {NORMALIZE_EXCHANGE_SQL}
                WHERE exchange IS NOT NULL
                """
            )

            cur.execute("SET session_replication_role = DEFAULT")
            conn.commit()

            print_counts(
                cur,
                "after stocks suffix:",
                "select split_part(ts_code, '.', 2) as suffix, count(*) from stocks group by 1 order by 2 desc",
            )
            print_counts(
                cur,
                "after stocks exchange:",
                "select exchange, count(*) from stocks group by 1 order by 2 desc",
            )
        print("normalize-stock-codes: done")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
