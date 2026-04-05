from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import User
from app.schemas.stock_schema import AttentionResponse
from app.services.attention_service import AttentionService

router = APIRouter()


class AttentionCreateRequest(BaseModel):
    code: str
    group: str = "watch"
    notes: str | None = None
    alert_conditions: dict[str, Any] | None = None


class AttentionUpdateRequest(BaseModel):
    group: str | None = None
    notes: str | None = None
    alert_conditions: dict[str, Any] | None = None


@router.get("/attention", response_model=list[AttentionResponse])
async def get_attention_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AttentionService(db)
    return await service.get_list(user_id=current_user.id)


@router.post("/attention")
async def add_attention(
    payload: AttentionCreateRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AttentionService(db)
    return await service.add(
        code=payload.code,
        user_id=current_user.id,
        group=payload.group,
        notes=payload.notes,
        alert_conditions=payload.alert_conditions,
    )


@router.put("/attention/{attention_id}")
async def update_attention(
    attention_id: int,
    payload: AttentionUpdateRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AttentionService(db)
    return await service.update(
        attention_id=attention_id,
        user_id=current_user.id,
        updates=payload.model_dump(exclude_none=True),
    )


@router.delete("/attention/{code}")
async def remove_attention(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AttentionService(db)
    return await service.remove(code, user_id=current_user.id)
