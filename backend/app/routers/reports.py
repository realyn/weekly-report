from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import asyncio
import logging
from app.database import get_db, async_session
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.services import report_service
from app.utils.security import get_current_user
from app.utils.date_utils import get_current_week, is_within_deadline, get_deadline_info
from app.models.user import User
from app.models.report import ReportStatus

router = APIRouter(prefix="/api/reports", tags=["周报"])
logger = logging.getLogger(__name__)


async def run_llm_analysis_background(year: int, week_num: int):
    """后台运行 LLM 分析"""
    from app.services.summary_service import trigger_llm_analysis
    try:
        async with async_session() as db:
            await trigger_llm_analysis(db, year, week_num)
    except Exception as e:
        logger.exception(f"后台 LLM 分析失败: {year}年第{week_num}周")


@router.get("/current", response_model=Optional[ReportResponse])
async def get_current_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    year, week_num = get_current_week()
    report = await report_service.get_user_report(db, current_user.id, year, week_num)
    return report


@router.get("/deadline")
async def get_report_deadline(
    year: Optional[int] = None,
    week: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """获取指定周的周报修改截止时间"""
    if not year or not week:
        year, week = get_current_week()
    info = await get_deadline_info(year, week)
    return {
        "code": 200,
        "data": {
            "year": year,
            "week": week,
            "deadline": info["deadline"].isoformat(),
            "deadline_str": info["deadline_str"],
            "is_expired": info["is_expired"],
            "remaining": info["remaining"]
        }
    }


@router.get("/", response_model=list[ReportResponse])
async def get_reports(
    year: Optional[int] = None,
    week_num: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not year:
        year, _ = get_current_week()
    reports = await report_service.get_reports(db, year, week_num, current_user.id)
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report_by_id(db, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="周报不存在")
    return report


@router.post("/", response_model=ReportResponse)
async def create_report(
    report_data: ReportCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    existing = await report_service.get_user_report(
        db, current_user.id, report_data.year, report_data.week_num
    )
    if existing:
        raise HTTPException(status_code=400, detail="该周周报已存在")
    report = await report_service.create_report(db, current_user.id, report_data)

    # 如果是提交状态，触发后台 LLM 分析
    if report_data.status == ReportStatus.submitted:
        background_tasks.add_task(run_llm_analysis_background, report_data.year, report_data.week_num)

    return report


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_data: ReportUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report_by_id(db, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="周报不存在")

    # 已提交的周报：检查是否在截止时间内
    if report.status == ReportStatus.submitted:
        within_deadline = await is_within_deadline(report.year, report.week_num)
        if not within_deadline:
            raise HTTPException(status_code=400, detail="已超过修改截止时间，无法修改")

    # 记录原状态
    was_submitted = report.status == ReportStatus.submitted

    updated_report = await report_service.update_report(db, report, report_data)

    # 如果状态变为提交（或重新提交），触发后台 LLM 分析
    if report_data.status == ReportStatus.submitted:
        background_tasks.add_task(run_llm_analysis_background, report.year, report.week_num)

    return updated_report


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report_by_id(db, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="周报不存在")
    if report.status == ReportStatus.submitted:
        raise HTTPException(status_code=400, detail="已提交的周报不能删除")
    await report_service.delete_report(db, report)
    return {"message": "删除成功"}
