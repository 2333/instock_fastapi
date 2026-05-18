from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import User
from app.schemas.user_event_schema import UserEventTrackRequest, UserEventTrackResponse
from app.services.event_service import EventRateLimitExceeded, EventService

router = APIRouter(prefix="/events", tags=["事件"])


@router.post(
    "/track",
    response_model=UserEventTrackResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def track_user_event(
    payload: UserEventTrackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserEventTrackResponse:
    service = EventService(db)

    try:
        persisted = await service.track_event(user_id=current_user.id, payload=payload)
    except EventRateLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))

    return UserEventTrackResponse(accepted=True, persisted=persisted)
