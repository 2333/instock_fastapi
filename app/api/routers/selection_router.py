from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_provider
from app.database import get_db
from app.models.stock_model import SelectionCondition, User
from app.schemas.selection_schema import (
    ScreeningComparisonRequest,
    ScreeningComparisonResponse,
    ScreeningHistoryData,
    ScreeningHistoryResponse,
    ScreeningMetadataResponse,
    ScreeningQuery,
    ScreeningRequest,
    ScreeningRunData,
    ScreeningRunResponse,
    ScreeningTemplateListResponse,
    ScreeningTodaySummaryResponse,
    SelectionConditionCreate,
    SelectionConditionResponse,
    SelectionConditionsMetaResponse,
    SelectionHistoryResponse,
    SelectionRequest,
    SelectionResponse,
)
from app.services.selection_service import SelectionService
from core.providers.market_data_provider import MarketDataProvider

router = APIRouter()


@router.get("/selection/conditions", response_model=SelectionConditionsMetaResponse)
async def get_selection_conditions() -> SelectionConditionsMetaResponse:
    return SelectionService.get_conditions()


@router.get("/screening/metadata", response_model=ScreeningMetadataResponse)
async def get_screening_metadata() -> ScreeningMetadataResponse:
    return ScreeningMetadataResponse(data=SelectionService.get_screening_metadata())


@router.get("/selection/templates", response_model=ScreeningTemplateListResponse)
async def get_selection_templates() -> ScreeningTemplateListResponse:
    """Return predefined screening condition templates for quick actions."""
    templates = SelectionService.get_templates()
    return ScreeningTemplateListResponse(data=templates)


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


@router.post("/selection", response_model=SelectionResponse)
async def run_selection(
    request: SelectionRequest = Body(...),
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> SelectionResponse:
    """Selection endpoint using provider-based service."""
    service = SelectionService(db=db, provider=provider)
    conditions = request.filters.model_dump(by_alias=True, exclude_none=True)
    if request.scope.market and "market" not in conditions:
        conditions["market"] = request.scope.market
    items = await service.run_selection(conditions, date, limit=request.scope.limit)
    return SelectionResponse(data=items)


@router.post("/screening/run", response_model=ScreeningRunResponse)
async def run_screening(
    request: ScreeningRequest = Body(...),
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> ScreeningRunResponse:
    """Main screening endpoint with provider-based service."""
    service = SelectionService(db=db, provider=provider)
    conditions = request.filters.model_dump(by_alias=True, exclude_none=True)
    if request.scope.market and "market" not in conditions:
        conditions["market"] = request.scope.market
    items = await service.run_selection(conditions, date, limit=request.scope.limit)
    resolved_trade_date = (
        items[0]["trade_date"] if items else await service._resolve_trade_date(date)
    )
    return ScreeningRunResponse(
        data=ScreeningRunData(
            query=ScreeningQuery(
                filters=request.filters,
                scope=request.scope,
                trade_date=resolved_trade_date,
            ),
            items=items,
            total=len(items),
        )
    )


@router.get("/selection/history", response_model=SelectionHistoryResponse)
async def get_selection_history(
    date: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SelectionHistoryResponse:
    service = SelectionService(db)
    items = await service.get_history(date, limit)
    return SelectionHistoryResponse(data=items)


@router.get("/screening/history", response_model=ScreeningHistoryResponse)
async def get_screening_history(
    date: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScreeningHistoryResponse:
    service = SelectionService(db)
    items = await service.get_history(date, limit)
    return ScreeningHistoryResponse(
        data=ScreeningHistoryData(trade_date=date, limit=limit, items=items, total=len(items))
    )


@router.get("/selection/today-summary", response_model=ScreeningTodaySummaryResponse)
async def get_today_summary(
    date: str | None = None,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScreeningTodaySummaryResponse:
    service = SelectionService(db)
    summary = await service.get_today_summary(current_user.id, date=date, limit=limit)
    return ScreeningTodaySummaryResponse(data=summary)


@router.post("/screening/compare", response_model=ScreeningComparisonResponse)
async def compare_screening_results(
    request: ScreeningComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScreeningComparisonResponse:
    """Compare multiple screening history result sets."""
    service = SelectionService(db)
    results = await service.compare_results(request.history_ids)
    return ScreeningComparisonResponse(data=results)
