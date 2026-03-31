#!/usr/bin/env python3
"""
Tushare 数据回补测试脚本（dry-run）

测试内容：
1. Tushare token 加载是否正确
2. 能否成功获取股票列表
3. 能否成功获取日线数据
4. 数据格式是否正确
5. 批量处理逻辑是否正常

用法：
  PYTHONPATH=. uv run python scripts/test_backfill.py \
    --start 20250101 --end 20250201 --batch-size 10
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, '.')

from app.config import get_settings
from core.crawling.tushare_provider import TushareProvider
from core.crawling.base import AdjustType
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.stock_model import Stock

def parse_args():
    parser = argparse.ArgumentParser(description='Test backfill flow')
    parser.add_argument('--start', default='20250101', help='Start date')
    parser.add_argument('--end', default='20250201', help='End date')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size')
    return parser.parse_args()

async def test_tushare_connection():
    """测试 Tushare 连接"""
    print("\n=== 1. 测试 Tushare 连接 ===")
    
    # 注入环境变量
    settings = get_settings()
    if settings.TUSHARE_TOKEN:
        os.environ['TUSHARE_TOKEN'] = settings.TUSHARE_TOKEN
        print(f"✅ Token 注入: {settings.TUSHARE_TOKEN[:15]}...")
    else:
        print("❌ 未找到 TUSHARE_TOKEN")
        return False
    
    if settings.TUSHARE_HTTP_URL:
        os.environ['TUSHARE_HTTP_URL'] = settings.TUSHARE_HTTP_URL
        print(f"✅ HTTP URL 注入: {settings.TUSHARE_HTTP_URL}")
    
    # 初始化 Provider
    provider = TushareProvider()
    pro = provider._get_pro()
    
    if pro:
        print("✅ TushareProvider 初始化成功")
    else:
        print("❌ TushareProvider 初始化失败")
        return False
    
    # 测试简单 API 调用
    try:
        df = provider._call_pro('trade_cal', exchange='', start_date='20250101', end_date='20250131')
        if df is not None and not df.empty:
            print(f"✅ API 调用成功，返回 {len(df)} 行")
            print(f"   示例: {df.iloc[0].to_dict()}")
        else:
            print("❌ API 调用返回空")
            return False
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        return False
    
    return True

async def test_stock_list(engine):
    """测试获取股票列表"""
    print("\n=== 2. 测试获取股票列表 ===")
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # 查询活跃股票数量
        result = await session.execute(
            sa.select(sa.func.count()).select_from(Stock).where(Stock.list_status == 'L')
        )
        total = result.scalar()
        print(f"✅ 数据库中的活跃股票数: {total}")
        
        # 查询前 10 只股票
        result = await session.execute(
            sa.select(Stock.ts_code, Stock.symbol, Stock.name, Stock.exchange)
            .where(Stock.list_status == 'L')
            .limit(10)
        )
        stocks = result.fetchall()
        print(f"✅ 前 10 只股票:")
        for ts_code, symbol, name, exchange in stocks:
            print(f"   {ts_code} - {name} ({exchange})")
        
        return [{'ts_code': s[0], 'symbol': s[1], 'name': s[2], 'exchange': s[3]} for s in stocks]

async def test_fetch_kline(provider, stock):
    """测试获取单只股票日线"""
    print(f"\n=== 3. 测试获取 {stock['ts_code']} 日线 ===")
    
    try:
        bars = await provider.fetch_kline(
            code=stock['ts_code'],
            start_date='20250101',
            end_date='20250201',
            adjust=AdjustType.NO_ADJUST,
            period='daily'
        )
        
        if bars:
            print(f"✅ 获取到 {len(bars)} 条数据")
            print(f"   第一条: {bars[0]}")
            print(f"   最后一条: {bars[-1]}")
            return True, len(bars)
        else:
            print("⚠️  未获取到数据（可能停牌或日期范围错误）")
            return False, 0
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return False, 0

async def test_batch_fetch(provider, stocks, start_date, end_date):
    """测试批量获取"""
    print(f"\n=== 4. 测试批量获取（{len(stocks)} 只股票）===")
    
    success_count = 0
    total_bars = 0
    
    for idx, stock in enumerate(stocks, 1):
        print(f"[{idx}/{len(stocks)}] 处理 {stock['ts_code']}...", end="")
        
        try:
            bars = await provider.fetch_kline(
                code=stock['ts_code'],
                start_date=start_date,
                end_date=end_date,
                adjust=AdjustType.NO_ADJUST,
                period='daily'
            )
            
            if bars:
                print(f" ✅ {len(bars)} 条")
                success_count += 1
                total_bars += len(bars)
            else:
                print(" ⚠️  无数据")
        except Exception as e:
            print(f" ❌ {e}")
    
    print(f"\n批量测试结果:")
    print(f"  成功: {success_count}/{len(stocks)}")
    print(f"  总数据条数: {total_bars}")
    
    return success_count, total_bars

async def main():
    args = parse_args()
    
    print("=" * 60)
    print("Tushare 回补流程测试")
    print("=" * 60)
    print(f"日期范围: {args.start} 至 {args.end}")
    print(f"批次大小: {args.batch_size}")
    
    # 1. 测试 Tushare 连接
    if not await test_tushare_connection():
        print("\n❌ Tushare 连接测试失败，请检查配置")
        return 1
    
    # 2. 连接数据库
    print("\n=== 数据库连接 ===")
    settings = get_settings()
    engine = create_async_engine(
        settings.get_async_url(),
        echo=False
    )
    
    try:
        # 3. 测试获取股票列表
        test_stocks = await test_stock_list(engine)
        
        if not test_stocks:
            print("❌ 未获取到股票列表")
            return 1
        
        # 4. 测试单只股票获取
        provider = TushareProvider()
        success, bar_count = await test_fetch_kline(provider, test_stocks[0])
        
        if not success:
            print(f"\n⚠️  单只股票测试失败（可能是停牌或数据缺失）")
            print("   继续测试其他股票...")
        
        # 5. 测试批量获取（只测试批次大小）
        sample_stocks = test_stocks[:min(args.batch_size, len(test_stocks))]
        batch_success, batch_bars = await test_batch_fetch(provider, sample_stocks, args.start, args.end)
        
        # 6. 总结
        print("\n" + "=" * 60)
        print("测试总结:")
        print(f"  Tushare 连接: ✅")
        print(f"  股票列表获取: ✅ ({len(test_stocks)} 只)")
        print(f"  单只股票测试: {'✅' if success else '⚠️ 无数据'}")
        print(f"  批量测试: {batch_success}/{len(sample_stocks)} 成功，共 {batch_bars} 条数据")
        print("\n建议:")
        if batch_success > 0:
            print("  ✅ 测试通过，可以运行全量回补脚本")
            print(f"  💡 使用: uv run python scripts/full_backfill_tushare.py --start {args.start} --end {args.end} --batch-size 100")
        else:
            print("  ❌ 所有测试都失败，请检查:")
            print("     1. Tushare token 是否有权限")
            print("     2. 日期范围是否有数据")
            print("     3. 网络连接是否正常")
        
        print("=" * 60)
        
    finally:
        await engine.dispose()
    
    return 0

if __name__ == '__main__':
    import sqlalchemy as sa
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
