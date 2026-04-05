import hashlib
import time
from collections import deque

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_optional
from app.database import get_db
from app.models.stock_model import User
from app.models.user_event_model import UserEvent
from app.schemas.event_schema import UserEventTrackRequest, UserEventTrackResponse

router = APIRouter(prefix="/events", tags=["用户行为"])

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 100
_event_windows: dict[str, deque[float]] = {}


def _resolve_actor_key(request: Request, current_user: User | None) -> str:
    if current_user:
        return f"user:{current_user.id}"
    client_host = request.client.host if request.client else "anonymous"
    return f"ip:{client_host}"


def _is_rate_limited(actor_key: str, now: float) -> bool:
    window = _event_windows.setdefault(actor_key, deque())
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
    while window and window[0] <= cutoff:
        window.popleft()
    if len(window) >= _RATE_LIMIT_MAX_REQUESTS:
        return True
    window.append(now)
    return False


@router.post(
    "/track",
    response_model=UserEventTrackResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def track_event(
    request: Request,
    payload: UserEventTrackRequest,
    response: Response,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """记录用户行为事件，失败时静默降级，不影响主流程。"""
    actor_key = _resolve_actor_key(request, current_user)
    if _is_rate_limited(actor_key, time.time()):
        response.status_code = status.HTTP_202_ACCEPTED
        return UserEventTrackResponse(status="rate_limited")

    user_id = current_user.id if current_user else None

    ip = request.client.host if request.client else None
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else None

    event = UserEvent(
        user_id=user_id,
        event_type=payload.event_type,
        event_data=payload.event_data,
        page=payload.page,
        referrer=payload.referrer,
        ip_hash=ip_hash,
        user_agent=request.headers.get("user-agent"),
    )
    try:
        db.add(event)
        await db.commit()
    except Exception:
        await db.rollback()
        response.status_code = status.HTTP_202_ACCEPTED
        return UserEventTrackResponse(status="degraded")

    return UserEventTrackResponse()
