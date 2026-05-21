from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.jobs.tasks.optimization_task import schedule_optimization_job
from app.models.stock_model import User
from app.schemas.optimization_schema import (
    ParameterOptimizationBestResponse,
    ParameterOptimizationJobCreate,
    ParameterOptimizationJobListResponse,
    ParameterOptimizationJobResponse,
    ParameterOptimizationTrialListResponse,
)
from app.services.optimization_service import (
    OptimizationConflictError,
    OptimizationNotFoundError,
    OptimizationService,
    OptimizationValidationError,
)

router = APIRouter()


@router.post(
    "/optimization/jobs",
    response_model=ParameterOptimizationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_optimization_job(
    payload: ParameterOptimizationJobCreate,
    auto_start: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParameterOptimizationJobResponse:
    service = OptimizationService(db)
    try:
        job = await service.create_job(user_id=current_user.id, payload=payload)
    except OptimizationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if auto_start:
        schedule_optimization_job(job.id)
    return ParameterOptimizationJobResponse(data=job)


@router.get("/optimization/jobs", response_model=ParameterOptimizationJobListResponse)
async def list_optimization_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParameterOptimizationJobListResponse:
    service = OptimizationService(db)
    return ParameterOptimizationJobListResponse(
        data=await service.list_jobs(user_id=current_user.id, limit=limit)
    )


@router.get("/optimization/jobs/{job_id}", response_model=ParameterOptimizationJobResponse)
async def get_optimization_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParameterOptimizationJobResponse:
    service = OptimizationService(db)
    try:
        return ParameterOptimizationJobResponse(
            data=await service.get_job(job_id=job_id, user_id=current_user.id)
        )
    except OptimizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Optimization job not found") from exc


@router.delete("/optimization/jobs/{job_id}", response_model=ParameterOptimizationJobResponse)
async def cancel_optimization_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParameterOptimizationJobResponse:
    service = OptimizationService(db)
    try:
        return ParameterOptimizationJobResponse(
            data=await service.cancel_job(job_id=job_id, user_id=current_user.id)
        )
    except OptimizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Optimization job not found") from exc
    except OptimizationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/optimization/jobs/{job_id}/trials",
    response_model=ParameterOptimizationTrialListResponse,
)
async def list_optimization_trials(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParameterOptimizationTrialListResponse:
    service = OptimizationService(db)
    try:
        return ParameterOptimizationTrialListResponse(
            data=await service.list_trials(job_id=job_id, user_id=current_user.id)
        )
    except OptimizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Optimization job not found") from exc


@router.get(
    "/optimization/jobs/{job_id}/best",
    response_model=ParameterOptimizationBestResponse,
)
async def get_optimization_best(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ParameterOptimizationBestResponse:
    service = OptimizationService(db)
    try:
        return ParameterOptimizationBestResponse(
            data=await service.get_best(job_id=job_id, user_id=current_user.id)
        )
    except OptimizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Optimization job not found") from exc
