from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.services import report_service
from app.utils.security import get_current_user
from app.utils.date_utils import get_current_week
from app.models.user import User
from app.models.report import ReportStatus

router = APIRouter(prefix="/api/reports", tags=["周报"])


@router.get("/current", response_model=Optional[ReportResponse])
async def get_current_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    year, week_num = get_current_week()
    report = await report_service.get_user_report(db, current_user.id, year, week_num)
    return report


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    existing = await report_service.get_user_report(
        db, current_user.id, report_data.year, report_data.week_num
    )
    if existing:
        raise HTTPException(status_code=400, detail="该周周报已存在")
    return await report_service.create_report(db, current_user.id, report_data)


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_data: ReportUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report = await report_service.get_report_by_id(db, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="周报不存在")
    if report.status == ReportStatus.submitted and report_data.status != ReportStatus.draft:
        raise HTTPException(status_code=400, detail="已提交的周报不能修改")
    return await report_service.update_report(db, report, report_data)


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
