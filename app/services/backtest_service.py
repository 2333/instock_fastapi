from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any


class BacktestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "backtest_id": "bt_001",
            "status": "running",
            "total_trades": 0,
            "win_rate": 0.0,
            "profit": 0.0,
        }

    async def get_result(self, backtest_id: str) -> Dict[str, Any]:
        return {"backtest_id": backtest_id, "status": "completed"}
