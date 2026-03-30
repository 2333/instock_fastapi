#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SelectionService with Provider Support

重构 SelectionService 以支持 MarketDataProvider。
保持向后兼容：仍可接受 db 参数。
"""

from typing import Any, Dict, List, Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from core.providers.market_data_provider import MarketDataProvider
from .selection_service import SelectionService as OriginalSelectionService


class SelectionServiceWithProvider(OriginalSelectionService):
    """
    增强版 SelectionService，支持通过 MarketDataProvider 访问数据。

    如果提供了 provider，优先使用 provider；
    否则降级到直接 DB 访问（向后兼容）。
    """

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        provider: Optional[MarketDataProvider] = None
    ):
        super().__init__(db=db)
        self.provider = provider

    async def run_selection(
        self,
        conditions: dict[str, Any],
        date: str | None,
        limit: int = 300
    ) -> List[Dict[str, Any]]:
        """
        执行筛选（Provider版本）

        如果 provider 可用，使用 provider 获取数据；
        否则回退到原始 SQL 实现。
        """
        if self.provider:
            return await self._run_selection_with_provider(
                conditions, date, limit
            )
        else:
            # 向后兼容：使用原始实现
            return await super().run_selection(conditions, date, limit)

    async def _run_selection_with_provider(
        self,
        conditions: dict[str, Any],
        date: str | None,
        limit: int = 300
    ) -> List[Dict[str, Any]]:
        """
        使用 Provider 执行筛选

        流程：
        1. 获取股票列表（应用市场筛选）
        2. 获取日线数据（应用价格/涨跌幅筛选）
        3. 获取技术指标（RSI、MACD）
        4. 应用指标筛选条件
        5. 生成结果（包含命中证据）
        """
        try:
            # 1. 解析筛选条件
            price_min = conditions.get("priceMin")
            price_max = conditions.get("priceMax")
            change_min = conditions.get("changeMin")
            change_max = conditions.get("changeMax")
            market = conditions.get("market")  # "沪市", "深市", "创业板", "科创板"
            rsi_min = conditions.get("rsiMin")
            rsi_max = conditions.get("rsiMax")
            macd_bullish = conditions.get("macdBullish", False)
            macd_bearish = conditions.get("macdBearish", False)

            # 2. 获取目标交易日
            if date:
                target_date = date.fromisoformat(date)
            else:
                target_date = await self.provider.get_latest_trade_date()

            # 3. 获取股票列表（应用市场筛选）
            markets_map = {
                "sh": ["沪市"],      # 上交所
                "sz": ["深市"],      # 深交所
                "创业板": ["创业板"],
                "科创板": ["科创板"],
            }
            market_filters = markets_map.get(market) if market else None
            stock_list_df = await self.provider.get_stock_list(
                markets=market_filters,
                active_only=True
            )

            if stock_list_df.empty:
                return []

            codes = stock_list_df["code"].tolist()

            # 4. 获取日线数据
            bars_df = await self.provider.get_daily_bars(
                codes=codes,
                start_date=target_date,  # 简化：只取目标日
                end_date=target_date,
                adjusted=True
            )

            if bars_df.empty:
                return []

            # 5. 初步筛选：价格、涨跌幅
            filtered = bars_df.copy()
            if price_min is not None:
                filtered = filtered[filtered["close"] >= price_min]
            if price_max is not None:
                filtered = filtered[filtered["close"] <= price_max]
            if change_min is not None:
                filtered = filtered[filtered["pct_chg"] >= change_min]
            if change_max is not None:
                filtered = filtered[filtered["pct_chg"] <= change_max]

            # 6. 如果不需要指标筛选，直接返回
            if not (rsi_min or rsi_max or macd_bullish or macd_bearish):
                # 构造基本结果
                return self._format_basic_results(filtered, conditions, target_date)

            # 7. 获取技术指标
            # 为简化，获取所有技术指标然后筛选
            final_codes = filtered["code"].unique().tolist()
            technicals_dict = await self.provider.get_technicals(
                code=None,  # 传入 None 表示批量获取（需要 provider 支持）
                indicators=["rsi", "macd", "macd_signal"],
                start_date=target_date,
                end_date=target_date
            )

            # TODO: 这里需要根据 provider 返回的格式调整
            # 暂时返回空，等待 provider 实现完整

            return []  # Placeholder

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Provider-based selection failed: {e}")
            # 回退到原始实现
            if self.db:
                return await super().run_selection(conditions, date, limit)
            return []

    def _format_basic_results(
        self,
        df: pd.DataFrame,
        conditions: Dict[str, Any],
        trade_date: date
    ) -> List[Dict[str, Any]]:
        """
        格式化基本结果（不含指标筛选）
        """
        results = []
        for _, row in df.iterrows():
            pct = float(row.get("pct_chg", 0))
            close = float(row.get("close", 0))
            amount = float(row.get("amount", 0))

            # 构建证据
            evidence = self._build_simple_evidence(row, conditions)

            summary = self._build_simple_summary(row, conditions)

            results.append({
                "ts_code": row["ts_code"],
                "code": row["code"],
                "stock_name": row.get("stock_name", ""),
                "score": round(pct * 5 + min(amount / 1e8, 20), 4),
                "signal": "buy" if pct >= 2 else ("sell" if pct <= -2 else "hold"),
                "trade_date": trade_date,
                "date": trade_date,
                "close": close,
                "change_rate": pct,
                "amount": amount,
                "reason_summary": summary,
                "evidence": evidence,
                "reason": {"summary": summary, "evidence": evidence},
            })

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _build_simple_evidence(
        self,
        row: pd.Series,
        conditions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """构建简单证据（基于价格和涨跌幅）"""
        evidence = []

        if conditions.get("priceMin") is not None:
            value = float(conditions["priceMin"])
            evidence.append({
                "key": "close",
                "label": "Close",
                "value": float(row["close"]),
                "operator": ">=",
                "condition": value,
                "matched": row["close"] >= value,
            })

        if conditions.get("priceMax") is not None:
            value = float(conditions["priceMax"])
            evidence.append({
                "key": "close",
                "label": "Close",
                "value": float(row["close"]),
                "operator": "<=",
                "condition": value,
                "matched": row["close"] <= value,
            })

        if conditions.get("changeMin") is not None:
            value = float(conditions["changeMin"])
            evidence.append({
                "key": "change_rate",
                "label": "Daily change",
                "value": float(row["pct_chg"]),
                "operator": ">=",
                "condition": value,
                "matched": row["pct_chg"] >= value,
            })

        if conditions.get("changeMax") is not None:
            value = float(conditions["changeMax"])
            evidence.append({
                "key": "change_rate",
                "label": "Daily change",
                "value": float(row["pct_chg"]),
                "operator": "<=",
                "condition": value,
                "matched": row["pct_chg"] <= value,
            })

        return evidence

    def _build_simple_summary(
        self,
        row: pd.Series,
        conditions: Dict[str, Any]
    ) -> str:
        """构建简单的命中原因摘要"""
        parts = []
        if conditions.get("priceMin") is not None:
            parts.append(f"Close >= {conditions['priceMin']:.2f}")
        if conditions.get("priceMax") is not None:
            parts.append(f"Close <= {conditions['priceMax']:.2f}")
        if conditions.get("changeMin") is not None:
            parts.append(f"Change >= {conditions['changeMin']:.2f}%")
        if conditions.get("changeMax") is not None:
            parts.append(f"Change <= {conditions['changeMax']:.2f}%")

        if parts:
            return "; ".join(parts)
        else:
            return f"Included in screening (pct_chg={row.get('pct_chg', 0):.2f}%)"
