#!/usr/bin/env python3
"""
将现有表转换为TimescaleDB时序表

注意：需要先将trade_date字段从varchar转换为date类型
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy import text
from app.database import async_engine, sync_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def convert_to_hypertable():
    """将表转换为TimescaleDB时序表"""

    print(f"[{datetime.now()}] 开始转换TimescaleDB时序表...")

    with sync_engine.connect() as conn:
        # 1. 为daily_bars添加date类型的列
        print("处理 daily_bars 表...")
        try:
            conn.execute(
                text("""
                ALTER TABLE daily_bars 
                ADD COLUMN IF NOT EXISTS trade_date_dt DATE;
            """)
            )
            conn.commit()
            print("  - 添加 trade_date_dt 列")
        except Exception as e:
            print(f"  - 添加列失败(可能已存在): {e}")

        # 2. 更新数据
        try:
            conn.execute(
                text("""
                UPDATE daily_bars 
                SET trade_date_dt = TO_DATE(trade_date, 'YYYYMMDD')
                WHERE trade_date_dt IS NULL;
            """)
            )
            conn.commit()
            print("  - 更新 trade_date_dt 数据")
        except Exception as e:
            print(f"  - 更新数据失败: {e}")

        # 3. 创建时序表
        try:
            conn.execute(
                text("""
                SELECT create_hypertable(
                    'daily_bars', 
                    'trade_date_dt',
                    if_not_exists => TRUE
                );
            """)
            )
            conn.commit()
            print("  - 创建 hypertable 成功")
        except Exception as e:
            if "already a hypertable" in str(e) or "already exists" in str(e):
                print("  - 已经是 hypertable")
            else:
                print(f"  - 创建 hypertable 失败: {e}")

        # 4. 为indicators表添加日期列
        print("\n处理 indicators 表...")
        try:
            conn.execute(
                text("""
                ALTER TABLE indicators 
                ADD COLUMN IF NOT EXISTS trade_date_dt DATE;
            """)
            )
            conn.execute(
                text("""
                UPDATE indicators 
                SET trade_date_dt = TO_DATE(trade_date, 'YYYYMMDD')
                WHERE trade_date_dt IS NULL;
            """)
            )
            conn.commit()
            print("  - 添加并更新 trade_date_dt 列")
        except Exception as e:
            print(f"  - 处理失败: {e}")

        try:
            conn.execute(
                text("""
                SELECT create_hypertable(
                    'indicators', 
                    'trade_date_dt',
                    if_not_exists => TRUE
                );
            """)
            )
            conn.commit()
            print("  - 创建 hypertable 成功")
        except Exception as e:
            if "already a hypertable" in str(e) or "already exists" in str(e):
                print("  - 已经是 hypertable")
            else:
                print(f"  - 创建 hypertable 失败: {e}")

        # 5. 为patterns表添加日期列
        print("\n处理 patterns 表...")
        try:
            conn.execute(
                text("""
                ALTER TABLE patterns 
                ADD COLUMN IF NOT EXISTS trade_date_dt DATE;
            """)
            )
            conn.execute(
                text("""
                UPDATE patterns 
                SET trade_date_dt = TO_DATE(trade_date, 'YYYYMMDD')
                WHERE trade_date_dt IS NULL;
            """)
            )
            conn.commit()
            print("  - 添加并更新 trade_date_dt 列")
        except Exception as e:
            print(f"  - 处理失败: {e}")

        try:
            conn.execute(
                text("""
                SELECT create_hypertable(
                    'patterns', 
                    'trade_date_dt',
                    if_not_exists => TRUE
                );
            """)
            )
            conn.commit()
            print("  - 创建 hypertable 成功")
        except Exception as e:
            if "already a hypertable" in str(e) or "already exists" in str(e):
                print("  - 已经是 hypertable")
            else:
                print(f"  - 创建 hypertable 失败: {e}")

        # 6. 为fund_flows表添加日期列
        print("\n处理 fund_flows 表...")
        try:
            conn.execute(
                text("""
                ALTER TABLE fund_flows 
                ADD COLUMN IF NOT EXISTS trade_date_dt DATE;
            """)
            )
            conn.execute(
                text("""
                UPDATE fund_flows 
                SET trade_date_dt = TO_DATE(trade_date, 'YYYYMMDD')
                WHERE trade_date_dt IS NULL;
            """)
            )
            conn.commit()
            print("  - 添加并更新 trade_date_dt 列")
        except Exception as e:
            print(f"  - 处理失败: {e}")

        try:
            conn.execute(
                text("""
                SELECT create_hypertable(
                    'fund_flows', 
                    'trade_date_dt',
                    if_not_exists => TRUE
                );
            """)
            )
            conn.commit()
            print("  - 创建 hypertable 成功")
        except Exception as e:
            if "already a hypertable" in str(e) or "already exists" in str(e):
                print("  - 已经是 hypertable")
            else:
                print(f"  - 创建 hypertable 失败: {e}")

        # 7. 配置压缩策略
        print("\n配置压缩策略...")
        try:
            conn.execute(
                text("""
                ALTER TABLE daily_bars SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'ts_code'
                );
            """)
            )
            conn.execute(
                text("""
                SELECT add_compression_policy(
                    'daily_bars',
                    INTERVAL '90 days',
                    if_not_exists => TRUE
                );
            """)
            )
            conn.commit()
            print("  - daily_bars 压缩策略配置成功")
        except Exception as e:
            print(f"  - 压缩策略配置失败: {e}")

        # 8. 创建索引
        print("\n创建索引...")
        indexes = [
            ("ix_daily_bars_ts_code_dt", "daily_bars", "ts_code, trade_date_dt DESC"),
            ("ix_indicators_ts_code_dt", "indicators", "ts_code, trade_date_dt DESC"),
            ("ix_patterns_ts_code_dt", "patterns", "ts_code, trade_date_dt DESC"),
            ("ix_fund_flows_ts_code_dt", "fund_flows", "ts_code, trade_date_dt DESC"),
        ]

        for idx_name, table_name, columns in indexes:
            try:
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({columns});")
                )
                conn.commit()
                print(f"  - 创建索引: {idx_name}")
            except Exception as e:
                print(f"  - 索引创建失败 {idx_name}: {e}")

        print(f"\n[{datetime.now()}] TimescaleDB时序表转换完成!")


if __name__ == "__main__":
    convert_to_hypertable()
