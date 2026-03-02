#!/usr/bin/env python3
"""
回补前准备：
1) 检查 daily_bars 是否有重复键(ts_code, trade_date)
2) 可选清理重复（保留最新 id）
3) 尝试补齐唯一约束，提升批量 upsert 性能
"""

from __future__ import annotations

import os
from sqlalchemy import text

from app.database import sync_engine


def main() -> None:
    fix_duplicates = os.getenv("FIX_DUPLICATES", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    disable_compress = os.getenv("DISABLE_COMPRESSION_FOR_BACKFILL", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    with sync_engine.connect() as conn:
        dup_count = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                  SELECT ts_code, trade_date
                  FROM daily_bars
                  GROUP BY ts_code, trade_date
                  HAVING COUNT(*) > 1
                ) t
                """
            )
        ).scalar() or 0
        print(f"重复键组数: {dup_count}")

        if dup_count > 0 and fix_duplicates:
            print("开始清理重复数据...")
            conn.execute(
                text(
                    """
                    DELETE FROM daily_bars a
                    USING daily_bars b
                    WHERE a.ts_code = b.ts_code
                      AND a.trade_date = b.trade_date
                      AND a.id < b.id
                    """
                )
            )
            conn.commit()
            print("重复清理完成")

        compression_enabled = conn.execute(
            text(
                """
                SELECT COALESCE(compression_enabled, false)
                FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'daily_bars'
                """
            )
        ).scalar()
        if compression_enabled and disable_compress:
            print("检测到 daily_bars 已启用压缩，先关闭压缩并移除压缩策略...")
            conn.execute(text("SELECT remove_compression_policy('daily_bars', if_exists => true);"))
            conn.execute(text("ALTER TABLE daily_bars SET (timescaledb.compress = false);"))
            conn.commit()
            print("已关闭压缩，便于回补阶段高频写入与约束维护")

        try:
            conn.execute(
                text(
                    """
                    ALTER TABLE daily_bars
                    ADD CONSTRAINT uq_daily_bars_ts_code_trade_date_dt
                    UNIQUE (ts_code, trade_date, trade_date_dt)
                    """
                )
            )
            conn.commit()
            print("已创建唯一约束 uq_daily_bars_ts_code_trade_date_dt")
        except Exception as exc:
            conn.rollback()
            print(f"创建唯一约束失败（可能已存在或与 hypertable 约束冲突）: {exc}")


if __name__ == "__main__":
    main()
