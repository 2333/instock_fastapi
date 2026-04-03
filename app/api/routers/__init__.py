from fastapi import APIRouter

from app.api.routers import (
    alert_router,
    attention_router,
    auth_router,
    backtest_router,
    events_router,
    etf_router,
    fund_flow_router,
    indicator_router,
    market_router,
    pattern_router,
    report_router,
    selection_router,
    stock_router,
    strategy_router,
    strategy_social_router,
    optimization_router,
)

router = APIRouter()

router.include_router(stock_router.router, prefix="/api/v1")
router.include_router(etf_router.router, prefix="/api/v1")
router.include_router(indicator_router.router, prefix="/api/v1")
router.include_router(strategy_router.router, prefix="/api/v1")
router.include_router(pattern_router.router, prefix="/api/v1")
router.include_router(backtest_router.router, prefix="/api/v1")
router.include_router(selection_router.router, prefix="/api/v1")
router.include_router(fund_flow_router.router, prefix="/api/v1")
router.include_router(attention_router.router, prefix="/api/v1")
router.include_router(auth_router.router, prefix="/api/v1")
router.include_router(market_router.router, prefix="/api/v1")
router.include_router(events_router.router, prefix="/api/v1")
router.include_router(alert_router.router, prefix="/api/v1")
router.include_router(strategy_social_router.router, prefix="/api/v1")
router.include_router(optimization_router.router, prefix="/api/v1")
router.include_router(report_router.router, prefix="/api/v1")

__all__ = ["router"]
