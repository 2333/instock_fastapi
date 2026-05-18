from collections import defaultdict, deque
from datetime import timedelta
from threading import Lock
from time import monotonic

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import logger
from app.models.stock_model import UserEvent
from app.schemas.user_event_schema import UserEventTrackRequest


class EventRateLimitExceeded(Exception):
    pass


class EventService:
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = timedelta(minutes=1)
    EVENT_VERSION = 1
    _attempt_windows: dict[int, deque[float]] = defaultdict(deque)
    _attempt_lock = Lock()

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def reset_rate_limit_state(cls) -> None:
        with cls._attempt_lock:
            cls._attempt_windows.clear()

    async def track_event(self, *, user_id: int, payload: UserEventTrackRequest) -> bool:
        try:
            await self._enforce_rate_limit(user_id)
            await self._persist_event(user_id=user_id, payload=payload)
            return True
        except EventRateLimitExceeded:
            await self._safe_rollback()
            raise
        except Exception as exc:
            await self._safe_rollback()
            logger.warning(
                f"User event persistence failed for user_id={user_id}, event_type={payload.event_type}: {exc}"
            )
            return False

    async def _enforce_rate_limit(self, user_id: int) -> None:
        now = monotonic()
        cutoff = now - self.RATE_LIMIT_WINDOW.total_seconds()

        with self._attempt_lock:
            window = self._attempt_windows[user_id]
            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) >= self.RATE_LIMIT_REQUESTS:
                raise EventRateLimitExceeded("Too many event requests")

            window.append(now)

    async def _persist_event(self, *, user_id: int, payload: UserEventTrackRequest) -> None:
        event = UserEvent(
            user_id=user_id,
            event_type=payload.event_type,
            event_version=self.EVENT_VERSION,
            page=payload.page,
            referrer=payload.referrer,
            event_data=payload.event_data,
        )
        self.db.add(event)
        await self.db.commit()

    async def _safe_rollback(self) -> None:
        try:
            await self.db.rollback()
        except SQLAlchemyError:
            logger.warning("User event rollback failed")
