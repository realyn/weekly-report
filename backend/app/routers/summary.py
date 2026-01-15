from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import os
from app.database import get_db
from app.services.summary_service import get_weekly_summary, save_weekly_summary, get_chart_statistics, get_weekly_report_dashboard, trigger_llm_analysis
from app.services.word_generator import generate_weekly_word
from app.utils.security import get_current_user, get_current_admin
from app.utils.date_utils import get_current_week
from app.models.user import User

router = APIRouter(prefix="/api/summary", tags=["汇总"])


@router.get("/weekly")
async def weekly_summary(
    year: Optional[int] = None,
    week: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not year or not week:
        year, week = get_current_week()
    summary = await get_weekly_summary(db, year, week, current_user)
    return {"code": 200, "data": summary}


@router.get("/download/{year}/{week}")
async def download_word(
    year: int,
    week: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    summary = await get_weekly_summary(db, year, week, current_user)
    if not summary.get("reports"):
        raise HTTPException(status_code=404, detail="该周没有已提交的周报")

    doc_path = generate_weekly_word(summary)
    await save_weekly_summary(db, year, week, summary, doc_path)

    return FileResponse(
        doc_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(doc_path)
    )


@router.get("/chart-data")
async def get_chart_data(
    year: Optional[int] = None,
    start_week: Optional[int] = 1,
    end_week: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not year:
        year, current_week = get_current_week()
        end_week = end_week or current_week
    else:
        _, current_week = get_current_week()
        end_week = end_week or current_week

    # 确保周数范围有效
    start_week = max(1, min(start_week, 53))
    end_week = max(start_week, min(end_week, 53))

    data = await get_chart_statistics(db, year, start_week, end_week)
    return {"code": 200, "data": data}


@router.get("/dashboard")
async def get_dashboard(
    year: Optional[int] = None,
    week: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可视化面板数据"""
    if not year or not week:
        year, week = get_current_week()
    data = await get_weekly_report_dashboard(db, year, week, current_user)
    return {"code": 200, "data": data}


@router.get("/latest-week")
async def get_latest_submitted_week(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取有已提交周报的最新一周"""
    from sqlalchemy import select, func
    from app.models.report import Report, ReportStatus

    result = await db.execute(
        select(Report.year, Report.week_num)
        .where(Report.status == ReportStatus.submitted)
        .order_by(Report.year.desc(), Report.week_num.desc())
        .limit(1)
    )
    row = result.first()

    if row:
        return {"code": 200, "data": {"year": row[0], "week": row[1]}}
    else:
        # 如果没有提交的周报，返回当前周
        year, week = get_current_week()
        return {"code": 200, "data": {"year": year, "week": week}}


@router.get("/available-weeks")
async def get_available_weeks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取所有有已提交周报的年周列表"""
    from sqlalchemy import select
    from app.models.report import Report, ReportStatus

    result = await db.execute(
        select(Report.year, Report.week_num)
        .where(Report.status == ReportStatus.submitted)
        .group_by(Report.year, Report.week_num)
        .order_by(Report.year, Report.week_num)
    )
    rows = result.all()

    # 返回格式: {year: [week1, week2, ...]}
    data = {}
    for year, week in rows:
        if year not in data:
            data[year] = []
        data[year].append(week)

    return {"code": 200, "data": data}


@router.post("/trigger-analysis")
async def manual_trigger_analysis(
    year: Optional[int] = None,
    week: Optional[int] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """手动触发LLM项目分析（管理员）"""
    if not year or not week:
        year, week = get_current_week()

    try:
        await trigger_llm_analysis(db, year, week)
        return {"code": 200, "message": f"已触发 {year}年第{week}周 的项目分析"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
