from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import User
from app.schemas.stock_schema import AttentionResponse
from app.services.attention_service import AttentionService

router = APIRouter()


class AttentionCreateRequest(BaseModel):
    code: str


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
    return await service.add(payload.code, user_id=current_user.id)


@router.delete("/attention/{code}")
async def remove_attention(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AttentionService(db)
    return await service.remove(code, user_id=current_user.id)
