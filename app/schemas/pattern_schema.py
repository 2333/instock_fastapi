from pydantic import BaseModel


class PatternResponse(BaseModel):
    id: int | None = None
    ts_code: str | None = None
    trade_date: str | None = None
    pattern_name: str | None = None
    pattern_type: str | None = None
    confidence: float | None = None
    stock_name: str | None = None
    code: str | None = None
