from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import SelectionCondition, User
from app.services.selection_service import SelectionService

router = APIRouter()


class SelectionConditionCreate(BaseModel):
    name: str
    category: str
    description: str | None = None
    params: dict[str, Any] | None = None
    is_active: bool = True


class SelectionConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    category: str
    description: str | None
    params: dict[str, Any] | None
    is_active: bool


@router.get("/selection/conditions")
async def get_selection_conditions():
    return SelectionService.get_conditions()


@router.get("/selection/my-conditions", response_model=list[SelectionConditionResponse])
async def get_my_conditions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SelectionCondition).where(SelectionCondition.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/selection/my-conditions", response_model=SelectionConditionResponse)
async def create_condition(
    condition: SelectionConditionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SelectionCondition).where(
        SelectionCondition.user_id == current_user.id, SelectionCondition.name == condition.name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="条件名称已存在")

    new_condition = SelectionCondition(
        user_id=current_user.id,
        name=condition.name,
        category=condition.category,
        description=condition.description,
        params=condition.params,
        is_active=condition.is_active,
    )
    db.add(new_condition)
    await db.commit()
    await db.refresh(new_condition)
    return new_condition


@router.put("/selection/my-conditions/{condition_id}", response_model=SelectionConditionResponse)
async def update_condition(
    condition_id: int,
    condition: SelectionConditionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SelectionCondition).where(
        SelectionCondition.id == condition_id, SelectionCondition.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="条件不存在")

    existing.name = condition.name
    existing.category = condition.category
    existing.description = condition.description
    existing.params = condition.params
    existing.is_active = condition.is_active

    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/selection/my-conditions/{condition_id}")
async def delete_condition(
    condition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SelectionCondition).where(
        SelectionCondition.id == condition_id, SelectionCondition.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="条件不存在")

    await db.delete(existing)
    await db.commit()
    return {"status": "success", "message": "条件已删除"}


@router.post("/selection")
async def run_selection(
    conditions: dict[str, Any] = Body(...),
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SelectionService(db)
    return await service.run_selection(conditions, date)


@router.get("/selection/history")
async def get_selection_history(
    date: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SelectionService(db)
    return await service.get_history(date, limit)
