from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
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
from app.services.alert_subscription_service import AlertSubscriptionService
from app.services.screener_adapter import (
    build_saved_screener_persistence,
    get_saved_screener_schema_version,
    normalize_saved_screener_payload,
)
from app.services.selection_service import SelectionService

router = APIRouter()


def _serialize_selection_condition(condition: SelectionCondition) -> dict:
    canonical_definition, compatible_params, derived_definition_hash = (
        normalize_saved_screener_payload(
            params=getattr(condition, "params", None),
        )
    )
    return {
        "id": condition.id,
        "user_id": condition.user_id,
        "name": condition.name,
        "category": condition.category,
        "description": condition.description,
        "params": compatible_params,
        "definition": canonical_definition,
        "schema_version": getattr(condition, "schema_version", None)
        or get_saved_screener_schema_version(),
        "definition_version": getattr(condition, "definition_version", None) or 1,
        "definition_hash": getattr(condition, "definition_hash", None) or derived_definition_hash,
        "is_active": condition.is_active,
        "updated_at": getattr(condition, "updated_at", None)
        or getattr(condition, "created_at", None),
    }


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
    return [_serialize_selection_condition(item) for item in result.scalars().all()]


@router.get("/screening/templates", response_model=ScreeningTemplateListResponse)
async def get_screening_templates() -> ScreeningTemplateListResponse:
    return ScreeningTemplateListResponse(data=SelectionService.get_templates())


@router.post("/selection/my-conditions", response_model=SelectionConditionResponse)
async def create_condition(
    condition: SelectionConditionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    persistence = build_saved_screener_persistence(
        params=condition.params,
        definition=condition.definition,
    )
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
        params=persistence["definition"],
        schema_version=persistence["schema_version"],
        definition_version=persistence["definition_version"],
        definition_hash=persistence["definition_hash"],
        is_active=condition.is_active,
    )
    db.add(new_condition)
    await db.commit()
    await db.refresh(new_condition)
    return _serialize_selection_condition(new_condition)


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

    persistence = build_saved_screener_persistence(
        params=condition.params,
        definition=condition.definition,
        existing_params=existing.params,
        existing_definition_version=getattr(existing, "definition_version", None),
    )
    previous_definition_hash = getattr(existing, "definition_hash", None)
    previous_definition_version = getattr(existing, "definition_version", None)

    existing.name = condition.name
    existing.category = condition.category
    existing.description = condition.description
    existing.params = persistence["definition"]
    existing.schema_version = persistence["schema_version"]
    existing.definition_hash = persistence["definition_hash"]
    existing.definition_version = persistence["definition_version"]
    existing.is_active = condition.is_active

    await db.commit()
    if (hasattr(existing, "definition_version") or hasattr(existing, "definition_hash")) and (
        previous_definition_hash != persistence["definition_hash"]
        or previous_definition_version != persistence["definition_version"]
        or not condition.is_active
    ):
        await AlertSubscriptionService.mark_subscriptions_stale_for_screener(
            db,
            selection_condition_id=existing.id,
            reason=(
                "筛选器已停用，需要重新确认订阅"
                if not condition.is_active
                else "筛选器定义已变化，需要重新创建订阅"
            ),
        )
        await db.commit()
    await db.refresh(existing)
    return _serialize_selection_condition(existing)


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

    if hasattr(existing, "definition_version") or hasattr(existing, "definition_hash"):
        await AlertSubscriptionService.mark_subscriptions_stale_for_screener(
            db,
            selection_condition_id=existing.id,
            reason="筛选器已删除，需要重新创建订阅",
        )
    await db.delete(existing)
    await db.commit()
    return {"status": "success", "message": "条件已删除"}


@router.post("/selection", response_model=SelectionResponse)
async def run_selection(
    request: SelectionRequest = Body(...),
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SelectionResponse:
    """Run the canonical saved-screener adapter path."""
    service = SelectionService(db=db)
    canonical_definition, compatible_filters, _ = normalize_saved_screener_payload(
        params=request.filters.model_dump(by_alias=True, exclude_none=True),
        definition=request.definition,
        scope=request.scope,
    )
    items = await service.run_selection(
        compatible_filters,
        date,
        limit=request.scope.limit,
        definition=canonical_definition,
    )
    return SelectionResponse(data=items)


@router.post("/screening/run", response_model=ScreeningRunResponse)
async def run_screening(
    request: ScreeningRequest = Body(...),
    date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScreeningRunResponse:
    """Run the canonical saved-screener adapter path."""
    service = SelectionService(db=db)
    canonical_definition, compatible_filters, definition_hash = normalize_saved_screener_payload(
        params=request.filters.model_dump(by_alias=True, exclude_none=True),
        definition=request.definition,
        scope=request.scope,
    )
    items = await service.run_selection(
        compatible_filters,
        date,
        limit=request.scope.limit,
        definition=canonical_definition,
    )
    resolved_trade_date = (
        items[0]["trade_date"] if items else await service._resolve_trade_date(date)
    )
    resolved_scope = dict(canonical_definition.get("scope") or {})
    resolved_scope["limit"] = request.scope.limit
    return ScreeningRunResponse(
        data=ScreeningRunData(
            query=ScreeningQuery(
                filters=compatible_filters,
                scope=resolved_scope,
                definition=canonical_definition,
                definition_hash=definition_hash,
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
