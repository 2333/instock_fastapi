from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_optional
from app.database import get_db
from app.models.stock_model import User
from app.models.user_event_model import UserEvent

router = APIRouter()


@router.post("/track")
async def track_event(
    request: Request,
    event_type: str,
    event_data: dict[str, Any] | None = None,
    page: str | None = None,
    referrer: str | None = None,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """记录用户行为事件（异步写入，不影响主流程）"""
    # 速率限制：简单实现（可按用户/IP 限制）
    # 此处省略具体限流逻辑，由中间件或 Redis 处理

    user_id = current_user.id if current_user else None

    # 提取 IP 并匿名化
    ip = request.client.host if request.client else None
    ip_hash = None
    if ip:
        import hashlib
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]

    event = UserEvent(
        user_id=user_id,
        event_type=event_type,
        event_data=event_data,
        page=page,
        referrer=referrer,
        ip_hash=ip_hash,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(event)
    await db.commit()

    return {"status": "ok"}
