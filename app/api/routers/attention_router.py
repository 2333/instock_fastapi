from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.schemas.stock_schema import AttentionResponse
from app.services.attention_service import AttentionService
from pydantic import BaseModel

router = APIRouter()

class AttentionCreateRequest(BaseModel):
    code: str


@router.get("/attention", response_model=List[AttentionResponse])
async def get_attention_list(db: AsyncSession = Depends(get_db)):
    service = AttentionService(db)
    return await service.get_list()


@router.post("/attention")
async def add_attention(
    payload: AttentionCreateRequest = Body(...), db: AsyncSession = Depends(get_db)
):
    service = AttentionService(db)
    return await service.add(payload.code)


@router.delete("/attention/{code}")
async def remove_attention(code: str, db: AsyncSession = Depends(get_db)):
    service = AttentionService(db)
    return await service.remove(code)
