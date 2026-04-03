import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.stock_model import Attention
from app.models.report_models import UserReport, ReportPreference
from app.models.user_event_model import UserEvent
from app.schemas.report_schema import ReportGenerateRequest, UserReportResponse
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_daily_market_report(
        self,
        user_id: int,
        report_date: date,
    ) -> Dict[str, Any]:
        """生成每日市场晨报"""
        # TODO: 接入真实市场数据
        # 当前返回框架结构

        # 获取用户关注列表
        attention_list = await self._get_user_attention(user_id)

        # 获取关注股票最新表现
        attention_performance = await self._get_attention_performance(attention_list, report_date)

        # 生成 HTML
        html = await self._render_daily_report_html(
            date=report_date,
            attention_performance=attention_performance,
        )

        return {
            "title": f"{report_date} 市场晨报",
            "report_type": "daily",
            "report_date": datetime.combine(report_date, datetime.min.time()),
            "html_content": html,
            "sections": [
                {"type": "market_summary", "data": {}},
                {"type": "attention_performance", "data": attention_performance},
                {"type": "insights", "data": {}},
            ],
        }

    async def generate_weekly_review(
        self,
        user_id: int,
        week_start: date,
    ) -> Dict[str, Any]:
        """生成每周操作回顾"""
        week_end = week_start + timedelta(days=6)

        # 统计本周行为
        stats = await self._get_weekly_stats(user_id, week_start, week_end)

        html = await self._render_weekly_report_html(
            week_start=week_start,
            week_end=week_end,
            stats=stats,
        )

        return {
            "title": f"{week_start} ~ {week_end} 操作回顾",
            "report_type": "weekly",
            "report_date": datetime.combine(week_end, datetime.max.time()),
            "html_content": html,
            "sections": [
                {"type": "screening_performance", "data": stats.get("screening", {})},
                {"type": "backtest_summary", "data": stats.get("backtest", {})},
                {"type": "attention_changes", "data": stats.get("attention", {})},
                {"type": "behavior_insights", "data": stats.get("insights", {})},
            ],
        }

    async def generate_monthly_summary(
        self,
        user_id: int,
        month: date,
    ) -> Dict[str, Any]:
        """生成月度策略总结"""
        # 月度统计
        stats = await self._get_monthly_stats(user_id, month)

        html = await self._render_monthly_report_html(
            month=month,
            stats=stats,
        )

        return {
            "title": f"{month.strftime('%Y年%m月')} 策略总结",
            "report_type": "monthly",
            "report_date": datetime(month.year, month.month, 1),
            "html_content": html,
            "sections": [
                {"type": "portfolio_performance", "data": stats.get("portfolio", {})},
                {"type": "backtest_analysis", "data": stats.get("backtest", {})},
                {"type": "behavior_analysis", "data": stats.get("behavior", {})},
                {"type": "recommendations", "data": stats.get("recommendations", {})},
            ],
        }

    async def save_report(
        self,
        user_id: int,
        report_data: Dict[str, Any],
        sent_via: List[str] = None,
    ) -> UserReport:
        """保存报告到数据库"""
        report = UserReport(
            user_id=user_id,
            report_type=report_data["report_type"],
            report_date=report_data["report_date"],
            html_content=report_data["html_content"],
            sent_via=sent_via or ["in_app"],
            sent_at=datetime.utcnow() if sent_via else None,
        )
        self.db.add(report)
        await self.db.flush()
        await self.db.refresh(report)
        return report

    async def create_notification(
        self,
        user_id: int,
        report: UserReport,
    ) -> None:
        """创建应用内通知"""
        from app.models.alert_models import Notification

        notif = Notification(
            user_id=user_id,
            type="report_available",
            title=f"您的{report.report_type}报告已生成",
            message=f"点击查看 {report.report_date.strftime('%Y-%m-%d')} 的{report.report_type}报告",
            payload={"report_id": report.id, "report_type": report.report_type},
        )
        self.db.add(notif)
        await self.db.flush()

    # --- 数据查询辅助方法 ---

    async def _get_user_attention(self, user_id: int) -> List[Attention]:
        """获取用户关注列表"""
        result = await self.db.execute(
            select(Attention).where(Attention.user_id == user_id)
        )
        return list(result.scalars().all())

    async def _get_attention_performance(
        self,
        attention_list: List[Attention],
        report_date: date,
    ) -> List[Dict[str, Any]]:
        """获取关注股票表现（简化：返回占位数据）"""
        # TODO: 连接 DailyBar 计算真实涨跌幅
        return [
            {
                "code": att.code,
                "name": att.stock_name or att.code,
                "change": 0.0,  # 待计算
                "change_pct": 0.0,
            }
            for att in attention_list[:10]  # 最多展示 10 只
        ]

    async def _get_weekly_stats(
        self,
        user_id: int,
        start: date,
        end: date,
    ) -> Dict[str, Any]:
        """获取本周统计"""
        # 统计筛选执行次数
        screening_count = await self._count_user_events(user_id, "filter_run", start, end)
        # 统计回测执行次数
        backtest_count = await self._count_user_events(user_id, "backtest_run", start, end)
        # 统计关注变化
        attention_add = await self._count_attention_changes(user_id, "add", start, end)

        return {
            "screening": {"count": screening_count},
            "backtest": {"count": backtest_count},
            "attention": {"added": attention_add},
            "insights": {"message": "本周你频繁使用 RSI 筛选，建议关注估值较低的大盘股。"},
        }

    async def _get_monthly_stats(
        self,
        user_id: int,
        month: date,
    ) -> Dict[str, Any]:
        """获取月度统计"""
        start = month.replace(day=1)
        if month.month == 12:
            end = month.replace(year=month.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = month.replace(month=month.month + 1, day=1) - timedelta(days=1)

        screening_count = await self._count_user_events(user_id, "filter_run", start, end)
        backtest_count = await self._count_user_events(user_id, "backtest_run", start, end)
        pattern_views = await self._count_user_events(user_id, "pattern_view", start, end)

        return {
            "portfolio": {"value": 0},  # TODO: 计算关注组合收益
            "backtest": {"count": backtest_count, "avg_sharpe": 0.0},
            "behavior": {
                "screening": screening_count,
                "pattern_views": pattern_views,
                "preference": "RSI 策略",
            },
            "recommendations": {"message": "建议下月尝试 MA 交叉策略"},
        }

    async def _count_user_events(
        self,
        user_id: int,
        event_type: str,
        start: date,
        end: date,
    ) -> int:
        """统计用户事件数量"""
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        result = await self.db.execute(
            select(func.count(UserEvent.id)).where(
                UserEvent.user_id == user_id,
                UserEvent.event_type == event_type,
                UserEvent.created_at >= start_dt,
                UserEvent.created_at <= end_dt,
            )
        )
        return result.scalar_one() or 0

    async def _count_attention_changes(
        self,
        user_id: int,
        action: str,
        start: date,
        end: date,
    ) -> int:
        """统计关注变更次数"""
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        result = await self.db.execute(
            select(func.count(UserEvent.id)).where(
                UserEvent.user_id == user_id,
                UserEvent.event_type == "attention_action",
                UserEvent.event_data["action"].astext == action,
                UserEvent.created_at >= start_dt,
                UserEvent.created_at <= end_dt,
            )
        )
        return result.scalar_one() or 0

    # --- HTML 渲染（简化版）---

    async def _render_daily_report_html(
        self,
        date: date,
        attention_performance: List[Dict[str, Any]],
    ) -> str:
        """渲染每日报告 HTML"""
        rows = ""
        for item in attention_performance:
            change_class = "up" if item["change_pct"] >= 0 else "down"
            rows += f"""
            <tr>
              <td>{item['code']}</td>
              <td>{item['name']}</td>
              <td class="{change_class}">{item['change_pct']:+.2f}%</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <style>
            body {{ font-family: -apple-system, sans-serif; margin: 0; padding: 20px; }}
            .header {{ border-bottom: 2px solid #2962FF; padding-bottom: 12px; margin-bottom: 20px; }}
            .section {{ margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
            .up {{ color: #00C853; }}
            .down {{ color: #FF5252; }}
            .insight {{ background: #f5f5f5; padding: 12px; border-radius: 6px; }}
          </style>
        </head>
        <body>
          <div class="header">
            <h1>📈 {date} 市场晨报</h1>
            <p>早上好，以下是今日市场简报：</p>
          </div>

          <div class="section">
            <h2>市场概览</h2>
            <p>（待接入实时行情数据）</p>
          </div>

          <div class="section">
            <h2>我的关注表现</h2>
            <table>
              <thead><tr><th>代码</th><th>名称</th><th>涨跌幅</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>
          </div>

          <div class="section">
            <h2>💡 操作建议</h2>
            <div class="insight">
              你近期频繁查看 RSI 超卖形态，建议关注估值较低的大盘股。
            </div>
          </div>
        </body>
        </html>
        """
        return html

    async def _render_weekly_report_html(
        self,
        week_start: date,
        week_end: date,
        stats: Dict[str, Any],
    ) -> str:
        """渲染周报 HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><style>body{{font-family:sans-serif;margin:20px}}</style></head>
        <body>
          <h1>📊 {week_start} ~ {week_end} 操作回顾</h1>
          <p>本周你共执行筛选 {stats['screening']['count']} 次，回测 {stats['backtest']['count']} 次。</p>
          <p>{stats['insights']['message']}</p>
        </body>
        </html>
        """

    async def _render_monthly_report_html(
        self,
        month: date,
        stats: Dict[str, Any],
    ) -> str:
        """渲染月报 HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><style>body{{font-family:sans-serif;margin:20px}}</style></head>
        <body>
          <h1>📋 {month.strftime('%Y年%m月')} 策略总结</h1>
          <p>本月你共执行筛选 {stats['behavior']['screening']} 次，查看形态 {stats['behavior']['pattern_views']} 次。</p>
          <p>偏好策略：{stats['behavior']['preference']}</p>
          <p>建议：{stats['recommendations']['message']}</p>
        </body>
        </html>
        """
