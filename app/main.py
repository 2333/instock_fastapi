import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import get_settings
from app.api.routers import stock_router, etf_router, indicator_router, strategy_router
from app.api.routers import (
    pattern_router,
    backtest_router,
    selection_router,
    fund_flow_router,
    attention_router,
    auth_router,
    market_router,
)
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.database import init_db, close_db
from app.logging_config import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting InStock API...")
    await init_db()
    logger.info("Database initialized")
    scheduler_started = start_scheduler()
    if scheduler_started:
        logger.info("Scheduler started")
    else:
        logger.info("Scheduler skipped in this worker")
    yield
    await close_db()
    stop_scheduler()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="InStock API",
    description="股票分析系统 API 文档 | Stock Analysis API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


cors_origins = settings.get_cors_origins()
cors_allow_credentials = settings.CORS_ALLOW_CREDENTIALS
if "*" in cors_origins and cors_allow_credentials:
    logger.warning(
        "CORS_ALLOW_ORIGINS='*' is incompatible with credentials; disabling credentials."
    )
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or [],
    allow_credentials=cors_allow_credentials,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)

WEB_DIR = Path(__file__).parent.parent / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.include_router(stock_router.router, prefix="/api/v1")
app.include_router(etf_router.router, prefix="/api/v1")
app.include_router(indicator_router.router, prefix="/api/v1")
app.include_router(strategy_router.router, prefix="/api/v1")
app.include_router(pattern_router.router, prefix="/api/v1")
app.include_router(backtest_router.router, prefix="/api/v1")
app.include_router(selection_router.router, prefix="/api/v1")
app.include_router(fund_flow_router.router, prefix="/api/v1")
app.include_router(attention_router.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(market_router.router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/info")
async def api_info():
    return {
        "name": "InStock API",
        "version": "1.0.0",
        "description": "股票分析系统 API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback

    logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
