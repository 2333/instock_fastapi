from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import BacktestResult, Strategy, StrategyResult, User
from app.schemas.strategy_schema import (
    StrategyResponse,
    StrategyResultResponse,
    StrategySelectionCreateRequest,
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


_STRATEGY_CORE_LOAD_FIELDS = (
    Strategy.id,
    Strategy.user_id,
    Strategy.name,
    Strategy.description,
    Strategy.params,
    Strategy.is_active,
)
_STRATEGY_CORE_REFRESH_FIELDS = [
    "id",
    "user_id",
    "name",
    "description",
    "params",
    "is_active",
]


def _strategy_core_stmt(*conditions):
    stmt = select(Strategy).options(load_only(*_STRATEGY_CORE_LOAD_FIELDS))
    if conditions:
        stmt = stmt.where(*conditions)
    return stmt


def _normalize_strategy_params(
    params: dict[str, Any] | None, *, default_source: str | None = None
) -> dict[str, Any] | None:
    return StrategyService.build_strategy_params(params, default_source=default_source)


def _serialize_strategy(strategy: Strategy) -> dict[str, Any]:
    return {
        "id": strategy.id,
        "user_id": strategy.user_id,
        "name": strategy.name,
        "description": strategy.description,
        "params": _normalize_strategy_params(strategy.params),
        "is_active": strategy.is_active,
    }


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
    stmt = _strategy_core_stmt(Strategy.user_id == current_user.id)
    result = await db.execute(stmt)
    return [_serialize_strategy(item) for item in result.scalars().all()]


@router.post("/strategies/my", response_model=StrategyListResponse)
async def create_strategy(
    strategy: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy.id).where(
        Strategy.user_id == current_user.id, Strategy.name == strategy.name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="策略名称已存在")

    normalized_params = _normalize_strategy_params(strategy.params)
    new_strategy = Strategy(
        user_id=current_user.id,
        name=strategy.name,
        description=strategy.description,
        params=normalized_params,
        is_active=strategy.is_active,
    )
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy, attribute_names=_STRATEGY_CORE_REFRESH_FIELDS)
    return _serialize_strategy(new_strategy)


@router.post("/strategies/my/from-selection", response_model=StrategyListResponse)
async def create_strategy_from_selection(
    payload: StrategySelectionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Strategy.id).where(
        Strategy.user_id == current_user.id, Strategy.name == payload.name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="策略名称已存在")

    normalized_params = _normalize_strategy_params(payload.params, default_source="selection")

    new_strategy = Strategy(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        params=normalized_params,
        is_active=payload.is_active,
    )
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy, attribute_names=_STRATEGY_CORE_REFRESH_FIELDS)
    return _serialize_strategy(new_strategy)


@router.put("/strategies/my/{strategy_id}", response_model=StrategyListResponse)
async def update_strategy(
    strategy_id: int,
    strategy: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = _strategy_core_stmt(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="策略不存在")

    if strategy.name is not None:
        duplicate_stmt = select(Strategy.id).where(
            Strategy.user_id == current_user.id,
            Strategy.name == strategy.name,
            Strategy.id != strategy_id,
        )
        duplicate_result = await db.execute(duplicate_stmt)
        duplicate_id = duplicate_result.scalar_one_or_none()
        if duplicate_id is not None:
            raise HTTPException(status_code=400, detail="策略名称已存在")
        existing.name = strategy.name
    if strategy.description is not None:
        existing.description = strategy.description
    if strategy.params is not None:
        existing.params = _normalize_strategy_params(strategy.params)
    if strategy.is_active is not None:
        existing.is_active = strategy.is_active

    await db.commit()
    await db.refresh(existing, attribute_names=_STRATEGY_CORE_REFRESH_FIELDS)
    return _serialize_strategy(existing)


@router.delete("/strategies/my/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = _strategy_core_stmt(Strategy.id == strategy_id, Strategy.user_id == current_user.id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="策略不存在")

    await db.execute(
        sqlalchemy_delete(StrategyResult).where(StrategyResult.strategy_id == existing.id)
    )
    await db.execute(
        sqlalchemy_update(BacktestResult)
        .where(BacktestResult.strategy_id == existing.id)
        .values(strategy_id=None)
    )
    await db.execute(sqlalchemy_delete(Strategy).where(Strategy.id == existing.id))
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
