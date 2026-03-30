from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import Strategy, User
from app.schemas.strategy_schema import (
    StrategyResponse,
    StrategyResultResponse,
    StrategyTemplateResponse,
)
from app.services.strategy_service import StrategyService

router = APIRouter()


class StrategyRunRequest(BaseModel):
    strategy: str | None = None
    date: str | None = None


class StrategyCreate(BaseModel):
    name: str
    description: str | None = None
    params: dict[str, Any] | None = None
    is_active: bool = True


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    params: dict[str, Any] | None = None
    is_active: bool | None = None


class StrategyListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None
    params: dict[str, Any] | None
    is_active: bool


@router.get("/strategies", response_model=list[StrategyResponse])
async def get_strategies():
    return StrategyService.get_strategy_list()


@router.get("/strategies/templates", response_model=list[StrategyTemplateResponse])
async def get_strategy_templates():
    return StrategyService.get_strategy_templates()


@router.get("/strategies/my", response_model=list[StrategyListResponse])
async def get_my_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy).where(Strategy.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/strategies/my", response_model=StrategyListResponse)
async def create_strategy(
    strategy: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy).where(
        Strategy.user_id == current_user.id, Strategy.name == strategy.name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="策略名称已存在")

    new_strategy = Strategy(
        user_id=current_user.id,
        name=strategy.name,
        description=strategy.description,
        params=strategy.params,
        is_active=strategy.is_active,
    )
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy)
    return new_strategy


@router.put("/strategies/my/{strategy_id}", response_model=StrategyListResponse)
async def update_strategy(
    strategy_id: int,
    strategy: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="策略不存在")

    if strategy.name is not None:
        existing.name = strategy.name
    if strategy.description is not None:
        existing.description = strategy.description
    if strategy.params is not None:
        existing.params = strategy.params
    if strategy.is_active is not None:
        existing.is_active = strategy.is_active

    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/strategies/my/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="策略不存在")

    await db.delete(existing)
    await db.commit()
    return {"status": "success", "message": "策略已删除"}


@router.post("/strategies/run")
async def run_strategy(
    strategy_name: str | None = Query(None, description="策略名称"),
    date: str | None = Query(None),
    payload: StrategyRunRequest | None = Body(None),
    db: AsyncSession = Depends(get_db),
):
    service = StrategyService(db)
    resolved_strategy = payload.strategy if payload and payload.strategy else strategy_name
    resolved_date = payload.date if payload and payload.date else date
    if not resolved_strategy:
        raise HTTPException(status_code=400, detail="strategy is required")
    return await service.run_strategy(resolved_strategy, resolved_date)


@router.get("/strategies/results", response_model=list[StrategyResultResponse])
async def get_strategy_results(
    strategy: str | None = Query(None),
    strategy_name: str | None = Query(None),
    date: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = StrategyService(db)
    resolved_strategy = strategy or strategy_name
    return await service.get_results(resolved_strategy, date, limit)
