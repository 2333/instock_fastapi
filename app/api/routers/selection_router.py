from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from app.database import get_db
from app.services.selection_service import SelectionService

router = APIRouter()


@router.get("/selection/conditions")
async def get_selection_conditions():
    return SelectionService.get_conditions()


@router.post("/selection")
async def run_selection(
    conditions: Dict[str, Any] = Body(...),
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    service = SelectionService(db)
    return await service.run_selection(conditions, date)


@router.get("/selection/history")
async def get_selection_history(
    date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = SelectionService(db)
    return await service.get_history(date, limit)
