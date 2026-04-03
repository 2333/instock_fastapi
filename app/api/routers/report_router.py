from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.stock_model import User
from app.schemas.report_schema import (
    ReportGenerateRequest,
    ReportPreferenceCreate,
    ReportPreferenceUpdate,
    ReportPreferenceResponse,
    UserReportResponse,
)
from app.services.report_generator import ReportGenerator
from app.core.dependencies import get_current_user
from app.models.report_models import ReportPreference

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# Dependency
async def get_report_generator() -> ReportGenerator:
    async with async_session_factory() as session:
        yield ReportGenerator(session)


# --- 报告列表与详情 ---

@router.get("/", response_model=list[UserReportResponse])
async def list_reports(
    report_type: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: ReportGenerator = Depends(get_report_generator),
):
    """获取我的报告列表"""
    from app.models.report_models import UserReport
    stmt = select(UserReport).where(UserReport.user_id == current_user.id)
    if report_type:
        stmt = stmt.where(UserReport.report_type == report_type)
    stmt = stmt.order_by(UserReport.created_at.desc()).limit(limit)
    result = await service.db.execute(stmt)
    reports = result.scalars().all()
    return [UserReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=UserReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    service: ReportGenerator = Depends(get_report_generator),
):
    """获取报告详情"""
    from app.models.report_models import UserReport
    report = await service.db.get(UserReport, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="报告不存在")
    return UserReportResponse.model_validate(report)


# --- 手动生成报告 ---

@router.post("/generate", response_model=UserReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    data: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    service: ReportGenerator = Depends(get_report_generator),
):
    """手动生成报告"""
    report_date = data.date.date() if data.date else date.today()

    # 根据类型调用生成器
    if data.report_type == "daily":
        report_data = await service.generate_daily_market_report(current_user.id, report_date)
    elif data.report_type == "weekly":
        week_start = report_date - timedelta(days=report_date.weekday())
        report_data = await service.generate_weekly_review(current_user.id, week_start)
    elif data.report_type == "monthly":
        report_data = await service.generate_monthly_summary(current_user.id, report_date.replace(day=1))
    else:
        raise HTTPException(status_code=400, detail="不支持的报告类型")

    # 保存报告
    sent_via = ["email"] if data.send_email else ["in_app"]
    report = await service.save_report(current_user.id, report_data, sent_via=sent_via)

    # 推送通知
    await service.create_notification(current_user.id, report)

    await service.db.commit()
    return UserReportResponse.model_validate(report)


# --- 偏好设置 ---

@router.get("/preferences", response_model=ReportPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    service: ReportGenerator = Depends(get_report_generator),
):
    """获取报告偏好设置"""
    from app.models.report_models import ReportPreference
    pref = await service.db.get(ReportPreference, current_user.id)
    if not pref:
        # 创建默认偏好
        pref = ReportPreference(user_id=current_user.id)
        service.db.add(pref)
        await service.db.flush()
        await service.db.refresh(pref)
    return ReportPreferenceResponse.model_validate(pref)


@router.put("/preferences", response_model=ReportPreferenceResponse)
async def update_preferences(
    data: ReportPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    service: ReportGenerator = Depends(get_report_generator),
):
    """更新报告偏好设置"""
    from app.models.report_models import ReportPreference
    pref = await service.db.get(ReportPreference, current_user.id)
    if not pref:
        pref = ReportPreference(user_id=current_user.id)
        service.db.add(pref)
        await service.db.flush()

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pref, key, value)

    await service.db.flush()
    await service.db.refresh(pref)
    return ReportPreferenceResponse.model_validate(pref)
