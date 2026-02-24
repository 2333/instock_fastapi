from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.schemas.stock_schema import FundFlowResponse
from app.services.fund_flow_service import FundFlowService

router = APIRouter()


@router.get("/fund-flow/{code}", response_model=List[FundFlowResponse])
async def get_fund_flow(
    code: str, days: int = Query(5, ge=1, le=30), db: AsyncSession = Depends(get_db)
):
    service = FundFlowService(db)
    return await service.get_fund_flow(code, days)


@router.get("/fund-flow/sector/industry")
async def get_industry_fund_flow(
    date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = FundFlowService(db)
    return await service.get_industry_fund_flow(date, limit)


@router.get("/fund-flow/sector/concept")
async def get_concept_fund_flow(
    date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = FundFlowService(db)
    return await service.get_concept_fund_flow(date, limit)
