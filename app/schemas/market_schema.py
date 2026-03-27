"""市场数据相关的 Schema 定义"""

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
