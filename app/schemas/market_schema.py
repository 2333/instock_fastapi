"""市场数据相关的 Schema 定义"""

from datetime import datetime

from pydantic import BaseModel, Field


class MarketMoverItem(BaseModel):
    """涨跌榜单项"""

    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    new_price: float = Field(..., description="最新价")
    change_rate: float = Field(..., description="涨跌幅(%)")
    ups_downs: float = Field(..., description="涨跌额")
    volume: float = Field(0, description="成交量")
    deal_amount: float = Field(0, description="成交额")
    turnoverrate: float = Field(0, description="换手率(%)")


class MarketMoversResponse(BaseModel):
    """涨跌榜响应"""

    type: str = Field(..., description="类型: gainers / losers")
    date: str = Field(..., description="数据日期")
    items: list[MarketMoverItem]
    total: int = Field(..., description="总条数")


class IndexItem(BaseModel):
    """指数数据项"""

    code: str = Field(..., description="指数代码, 如 sh000001")
    name: str = Field(..., description="指数名称")
    current: float = Field(..., description="当前点位")
    change: float = Field(..., description="涨跌点数")
    change_rate: float = Field(..., description="涨跌幅(%)")
    volume: float = Field(0, description="成交量(手)")
    amount: float = Field(0, description="成交额(万元)")
    high: float | None = Field(None, description="最高")
    low: float | None = Field(None, description="最低")
    open: float | None = Field(None, description="开盘")


class MarketIndicesResponse(BaseModel):
    """指数数据响应"""

    date: str
    items: list[IndexItem]


class StockListQuery(BaseModel):
    """股票列表查询参数（用于文档说明）"""

    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
    date: str | None = Field(None, description="日期 YYYY-MM-DD")
    sort_by: str | None = Field(None, description="排序字段")
    sort_order: str | None = Field("desc", description="排序方向 asc/desc")
    keyword: str | None = Field(None, description="搜索关键词(代码/名称)")


class MarketTaskDatasetStatus(BaseModel):
    """关键市场数据表的新鲜度摘要"""

    dataset: str = Field(..., description="数据集标识")
    latest_trade_date: str | None = Field(None, description="该数据集最新交易日")
    baseline_trade_date: str | None = Field(None, description="基准交易日，当前取 daily_bars 最新值")
    current: bool = Field(False, description="是否与基准交易日对齐")


class MarketTaskHealthAlert(BaseModel):
    """最近仍未恢复的抓取告警"""

    task_name: str
    entity_type: str
    entity_key: str
    trade_date: str | None = None
    status: str
    source: str | None = None
    note: str | None = None
    updated_at: datetime | None = None


class MarketTaskHealthResponse(BaseModel):
    """Phase 0 任务健康摘要"""

    baseline_trade_date: str | None = None
    datasets: list[MarketTaskDatasetStatus] = Field(default_factory=list)
    alerts: list[MarketTaskHealthAlert] = Field(default_factory=list)
    alert_count: int = 0
