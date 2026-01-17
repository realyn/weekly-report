from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
from app.database import get_db, async_session
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse, ParseResult, ParsePreviewRequest
from app.services import report_service
from app.services.report_parser_service import get_report_parser_service
from app.utils.security import get_current_user, get_current_admin
from app.utils.date_utils import get_current_week, is_within_deadline, get_deadline_info
from app.models.user import User, UserRole
from app.models.report import ReportStatus

router = APIRouter(prefix="/api/reports", tags=["周报"])
logger = logging.getLogger(__name__)


async def run_llm_analysis_background(year: int, week_num: int):
    """后台运行 LLM 分析"""
    from app.services.summary_service import trigger_llm_analysis
    try:
        async with async_session() as db:
            await trigger_llm_analysis(db, year, week_num)
    except Exception:
        logger.exception(f"后台 LLM 分析失败: {year}年第{week_num}周")


async def run_report_parse_background(report_id: int, this_week_work: str, next_week_plan: str):
    """后台解析周报内容为结构化条目"""
    from app.services.report_service import get_report_by_id
    try:
        parser = get_report_parser_service()
        async with async_session() as db:
            report = await get_report_by_id(db, report_id)
            if report:
                parse_result = await parser.parse_report_text(this_week_work, next_week_plan)
                await parser.save_parsed_items(db, report, parse_result)
    except Exception:
        logger.exception(f"后台周报解析失败: report_id={report_id}")


@router.get("/years")
async def get_available_years(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户有周报记录的年份列表"""
    years = await report_service.get_available_years(db, current_user.id)
    return years


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
    year, week = (year, week) if year and week else get_current_week()
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


@router.post("/parse-preview", response_model=ParseResult)
async def parse_preview(
    request: ParsePreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """解析周报文本预览（不保存）"""
    parser = get_report_parser_service()
    result = await parser.parse_report_text(request.this_week_work, request.next_week_plan)
    return result


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

    # 后台解析周报内容为结构化条目
    if report_data.this_week_work or report_data.next_week_plan:
        background_tasks.add_task(
            run_report_parse_background,
            report.id,
            report_data.this_week_work or "",
            report_data.next_week_plan or ""
        )

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

    updated_report = await report_service.update_report(db, report, report_data)

    # 如果内容有更新，后台重新解析
    if report_data.this_week_work is not None or report_data.next_week_plan is not None:
        this_week = report_data.this_week_work if report_data.this_week_work is not None else report.this_week_work
        next_week = report_data.next_week_plan if report_data.next_week_plan is not None else report.next_week_plan
        background_tasks.add_task(
            run_report_parse_background,
            report_id,
            this_week or "",
            next_week or ""
        )

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


@router.get("/admin/user/{user_id}", response_model=list[ReportResponse])
async def get_user_reports_admin(
    user_id: int,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """管理员查看指定用户的周报历史"""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    if not year:
        year, _ = get_current_week()
    reports = await report_service.get_reports(db, year, None, user_id)
    return reports
