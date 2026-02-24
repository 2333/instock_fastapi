import sys
from datetime import datetime
from pathlib import Path
from loguru import logger
from app.config import get_settings

settings = get_settings()

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{message}</cyan> | "
    "{file}:{line}"
)

logger.remove()

logger.add(
    sys.stdout,
    format=LOG_FORMAT,
    level=settings.LOG_LEVEL,
    colorize=True,
)

log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
logger.add(
    LOG_DIR / log_filename,
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
    enqueue=True,
)

logger.add(
    LOG_DIR / "error.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


def get_logger(name: str = __name__):
    return logger.bind(name=name)
