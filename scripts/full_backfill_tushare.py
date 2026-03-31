#!/usr/bin/env python3
"""
独立 Tushare 数据全量回补脚本

不依赖原项目代码中的任务逻辑，独立实现：
- 从 stocks 表获取所有股票
- 使用 TushareProvider 下载日线数据
- 写入 daily_bars 表
- 更新 backfill_daily_state 状态

用法：
  PYTHONPATH=. uv run python scripts/full_backfill_tushare.py \
    --start 20200101 --end 20251231 \
    --batch-size 100

⚠️  警告：此脚本会写入生产数据库，请先确保已备份！
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '.')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from app.config import get_settings
from core.crawling.tushare_provider import TushareProvider
from core.crawling.base import AdjustType
from app.models.stock_model import Stock, DailyBar

def parse_args():
    parser = argparse.ArgumentParser(description='Full backfill using Tushare')
    parser.add_argument('--start', default='20200101', help='Start date (YYYYMMDD)')
    parser.add_argument('--end', default='20251231', help='End date (YYYYMMDD)')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no DB write)')
    parser.add_argument('--resume', action='store_true', help='Resume from backfill_daily_state')
    return parser.parse_args()

async def get_async_engine():
    settings = get_settings()
    return create_async_engine(
        settings.get_async_url(),
        echo=False,
        pool_size=20,
        max_overflow=30
    )

async def get_all_stocks(session: AsyncSession) -> List[Dict]:
    """获取所有上市股票"""
    query = sa.select(
        Stock.ts_code,
        Stock.symbol,
        Stock.name,
        Stock.exchange
    ).where(Stock.list_status == 'L')
    
    result = await session.execute(query)
    stocks = result.fetchall()
    
    return [
        {
            'ts_code': row.ts_code,
            'symbol': row.symbol,
            'name': row.name,
            'exchange': row.exchange,
        }
        for row in stocks
    ]

async def get_backfill_state(session: AsyncSession) -> Dict[str, str]:
    """获取回补状态"""
    result = await session.execute(
        sa.text("SELECT ts_code, status FROM backfill_daily_state")
    )
    return {row[0]: row[1] for row in result.fetchall()}

async def update_backfill_state(session: AsyncSession, ts_code: str, status: str, note: str = ''):
    """更新回补状态"""
    stmt = sa.text("""
        INSERT INTO backfill_daily_state (ts_code, status, note, updated_at)
        VALUES (:ts_code, :status, :note, NOW())
        ON CONFLICT (ts_code) DO UPDATE SET
            status = :status,
            note = :note,
            updated_at = NOW()
    """)
    await session.execute(stmt, {
        'ts_code': ts_code,
        'status': status,
        'note': note
    })
    await session.commit()

async def save_daily_bars(session: AsyncSession, ts_code: str, bars: List[Dict]) -> int:
    """保存日线数据（upsert）"""
    from datetime import date
    
    saved_count = 0
    
    for bar in bars:
        try:
            trade_date = bar['date'].replace('-', '')
            
            # 检查是否已存在
            existing = await session.execute(
                sa.select(DailyBar).where(
                    DailyBar.ts_code == ts_code,
                    DailyBar.trade_date == trade_date
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # 创建新记录
            daily_bar = DailyBar(
                ts_code=ts_code,
                trade_date=trade_date,
                trade_date_dt=date(int(trade_date[:4]), int(trade_date[4:6]), int(trade_date[6:8])),
                open=float(bar['open']),
                high=float(bar['high']),
                low=float(bar['low']),
                close=float(bar['close']),
                pre_close=float(bar['pre_close']) if bar.get('pre_close') is not None else None,
                change=float(bar['change']) if bar.get('change') is not None else None,
                pct_chg=float(bar['change_pct']) if bar.get('change_pct') is not None else None,
                vol=float(bar['volume']) if bar.get('volume') is not None else None,
                amount=float(bar['amount']) if bar.get('amount') is not None else None,
                adj_factor=1.0
            )
            session.add(daily_bar)
            saved_count += 1
            
        except Exception as e:
            logger.error(f"Error saving bar for {ts_code}: {e}")
            continue
    
    await session.commit()
    return saved_count

async def process_batch(
    session: AsyncSession,
    provider: TushareProvider,
    stocks: List[Dict],
    start_date: str,
    end_date: str,
    dry_run: bool = False
) -> Tuple[int, List[str]]:
    """处理一批股票"""
    success_count = 0
    errors = []
    
    for stock in stocks:
        ts_code = stock['ts_code']
        
        try:
            # 调用 Tushare
            bars = await provider.fetch_kline(
                code=ts_code,
                start_date=start_date,
                end_date=end_date,
                adjust=AdjustType.NO_ADJUST,
                period='daily'
            )
            
            if not bars:
                msg = f"No data for {ts_code}"
                if not dry_run:
                    await update_backfill_state(session, ts_code, 'nodata', msg)
                errors.append(msg)
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] {ts_code}: would save {len(bars)} bars")
                success_count += 1
            else:
                saved = await save_daily_bars(session, ts_code, bars)
                await update_backfill_state(
                    session,
                    ts_code,
                    'done',
                    f"rows={saved},source=tushare"
                )
                logger.info(f"✅ {ts_code}: saved {saved}/{len(bars)} bars")
                success_count += 1
                
        except Exception as e:
            error_msg = f"Failed for {ts_code}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            if not dry_run:
                try:
                    await update_backfill_state(session, ts_code, 'error', str(e))
                except Exception:
                    pass
    
    return success_count, errors

async def main():
    args = parse_args()
    
    print("=" * 60)
    print("Tushare 全量数据回补")
    print("=" * 60)
    print(f"日期范围: {args.start} 至 {args.end}")
    print(f"批次大小: {args.batch_size}")
    print(f"Dry run: {args.dry_run}")
    print(f" Resume from state: {args.resume}")
    print("=" * 60)
    
    # 1. 设置环境变量
    settings = get_settings()
    if settings.TUSHARE_TOKEN:
        os.environ['TUSHARE_TOKEN'] = settings.TUSHARE_TOKEN
        logger.info(f"Token loaded: {settings.TUSHARE_TOKEN[:15]}...")
    else:
        logger.error("TUSHARE_TOKEN not configured!")
        return 1
    
    if settings.TUSHARE_HTTP_URL:
        os.environ['TUSHARE_HTTP_URL'] = settings.TUSHARE_HTTP_URL
    
    # 2. 初始化 TushareProvider
    provider = TushareProvider()
    if not provider._get_pro():
        logger.error("Failed to initialize TushareProvider")
        return 1
    
    logger.info("TushareProvider initialized OK")
    
    # 3. 连接数据库
    engine = await get_async_engine()
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    total_success = 0
    total_errors = []
    start_time = datetime.now()
    
    try:
        async with AsyncSessionLocal() as session:
            # 4. 获取股票列表
            logger.info("Fetching stock list from database...")
            all_stocks = await get_all_stocks(session)
            logger.info(f"Total active stocks: {len(all_stocks)}")
            
            # 5. 如果需要 resume，过滤已完成的
            if args.resume:
                logger.info("Loading backfill state for resume...")
                state = await get_backfill_state(session)
                pending_stocks = [s for s in all_stocks if state.get(s['ts_code']) not in ('done', 'nodata')]
                logger.info(f"Resume mode: {len(pending_stocks)} stocks pending (out of {len(all_stocks)})")
                all_stocks = pending_stocks
            
            # 6. 分批处理
            total_batches = (len(all_stocks) + args.batch_size - 1) // args.batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * args.batch_size
                end_idx = min(start_idx + args.batch_size, len(all_stocks))
                batch = all_stocks[start_idx:end_idx]
                
                logger.info(f"\n{'='*60}")
                logger.info(f"Batch {batch_idx + 1}/{total_batches} ({len(batch)} stocks)")
                logger.info(f"{'='*60}")
                
                success, errors = await process_batch(
                    session, provider, batch, args.start, args.end, args.dry_run
                )
                total_success += success
                total_errors.extend(errors)
                
                # 进度报告
                elapsed = datetime.now() - start_time
                processed = (batch_idx + 1) * args.batch_size
                remaining = len(all_stocks) - processed
                if processed > 0:
                    eta = elapsed / processed * remaining
                else:
                    eta = timedelta(0)
                
                logger.info(f"\nProgress: {processed}/{len(all_stocks)} | "
                          f"Success: {total_success} | Errors: {len(total_errors)}")
                logger.info(f"Elapsed: {elapsed} | ETA: {eta}")
            
            # 7. 最终统计
            logger.info("\n" + "=" * 60)
            logger.info("BACKFILL COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Total stocks processed: {len(all_stocks)}")
            logger.info(f"Successfully saved: {total_success}")
            logger.info(f"Errors/Warnings: {len(total_errors)}")
            logger.info(f"Total time: {datetime.now() - start_time}")
            
            if total_errors:
                logger.warning(f"\nSample errors (first 10):")
                for err in total_errors[:10]:
                    logger.warning(f"  {err}")
            
            # 8. 验证覆盖率
            if not args.dry_run:
                logger.info("\nVerifying coverage...")
                result = await session.execute(
                    sa.text("""
                        SELECT 
                            COUNT(DISTINCT ts_code) as covered,
                            (SELECT COUNT(*) FROM stocks WHERE list_status = 'L') as total
                        FROM daily_bars 
                        WHERE trade_date = (SELECT MAX(trade_date) FROM daily_bars)
                    """)
                )
                row = result.fetchone()
                if row:
                    covered, total = row
                    if total:
                        coverage = covered / total * 100
                        logger.info(f"Coverage for latest date: {covered}/{total} ({coverage:.1f}%)")
                        
                        if coverage < 90:
                            logger.warning(f"⚠️  Coverage is low! Target is >95%")
                        else:
                            logger.info(f"✅ Coverage is good!")
    
    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user. You can resume with --resume flag.")
        return 1
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
    finally:
        await engine.dispose()
    
    return 0

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
