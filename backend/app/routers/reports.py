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


async def save_user_parsed_items(
    db: AsyncSession,
    report_id: int,
    this_week_items: list,
    next_week_items: list
):
    """保存用户修正后的解析结果"""
    from sqlalchemy import delete
    from app.models.report import ReportItem, ItemType

    # 删除旧的 items
    await db.execute(delete(ReportItem).where(ReportItem.report_id == report_id))

    count = 0

    # 保存本周工作
    for i, item in enumerate(this_week_items or []):
        report_item = ReportItem(
            report_id=report_id,
            item_type=ItemType.this_week,
            project_name=item.project_name,
            content=item.content,
            sequence=i
        )
        db.add(report_item)
        count += 1

    # 保存下周计划
    for i, item in enumerate(next_week_items or []):
        report_item = ReportItem(
            report_id=report_id,
            item_type=ItemType.next_week,
            project_name=item.project_name,
            content=item.content,
            sequence=i
        )
        db.add(report_item)
        count += 1

    await db.commit()
    logger.info(f"保存用户修正的周报条目: report_id={report_id}, 共{count}条")


@router.get("/years")
async def get_available_years(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户有周报记录的年份列表"""
    years = await report_service.get_available_years(db, current_user.id)
    return years


@router.get("/projects")
async def get_project_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目列表（用于周报选择），包含子项信息和活跃度

    活跃度判断依据：
    - 日报：DailyReport.date 在最近30天内
    - 周报：Report 所属周的结束日期在最近30天内
    """
    from app.services.llm_service import get_project_extractor
    from app.models.report import Report, ReportItem
    from app.models.daily_report import DailyReport, DailyReportItem
    from sqlalchemy import func, select
    from datetime import datetime, timedelta, date

    extractor = get_project_extractor()
    data = extractor.load_known_projects()
    projects = data.get("projects", [])

    # 计算30天前的日期
    thirty_days_ago = date.today() - timedelta(days=30)

    # 统计日报中的项目使用次数（基于日报日期）
    daily_usage = await db.execute(
        select(DailyReportItem.project_name, func.count(DailyReportItem.id).label('count'))
        .join(DailyReport, DailyReportItem.daily_report_id == DailyReport.id)
        .where(DailyReport.date >= thirty_days_ago)
        .where(DailyReportItem.project_name.isnot(None))
        .group_by(DailyReportItem.project_name)
    )
    daily_counts = {row.project_name: row.count for row in daily_usage.fetchall()}

    # 统计周报中的项目使用次数（基于周报所属周）
    current_year, current_week = date.today().isocalendar()[:2]

    # 获取最近5周的周报数据（约35天覆盖30天）
    recent_weeks = []
    check_date = date.today()
    for _ in range(5):
        year, week = check_date.isocalendar()[:2]
        recent_weeks.append((year, week))
        check_date -= timedelta(days=7)

    # 查询这些周的周报条目
    report_counts = {}
    if recent_weeks:
        from sqlalchemy import or_, and_
        week_conditions = [
            and_(Report.year == year, Report.week_num == week)
            for year, week in recent_weeks
        ]
        report_usage = await db.execute(
            select(ReportItem.project_name, func.count(ReportItem.id).label('count'))
            .join(Report, ReportItem.report_id == Report.id)
            .where(or_(*week_conditions))
            .where(ReportItem.project_name.isnot(None))
            .group_by(ReportItem.project_name)
        )
        report_counts = {row.project_name: row.count for row in report_usage.fetchall()}

    # 合并使用次数（日报为主，周报为辅）
    usage_counts = {}
    for name, count in daily_counts.items():
        usage_counts[name] = usage_counts.get(name, 0) + count
    for name, count in report_counts.items():
        usage_counts[name] = usage_counts.get(name, 0) + count

    # 构建结果列表
    result = []
    for proj in projects:
        if proj.get("status") == "archived":
            continue
        name = proj["name"]
        usage = usage_counts.get(name, 0)
        item = {
            "name": name,
            "sub_items": [
                {"name": sub.get("name", "")}
                for sub in proj.get("sub_items", [])
                if sub.get("name")
            ],
            "is_active": usage > 0,
            "usage_count": usage
        }
        result.append(item)

    # 按活跃度排序：活跃在前，使用次数高的优先
    result.sort(key=lambda x: (-int(x["is_active"]), -x["usage_count"], x["name"]))

    return result


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

    # 保存解析结果：优先使用用户修正的结果
    if report_data.this_week_items is not None or report_data.next_week_items is not None:
        # 用户提供了修正后的解析结果，直接保存
        await save_user_parsed_items(
            db, report.id,
            report_data.this_week_items,
            report_data.next_week_items
        )
    elif report_data.this_week_work or report_data.next_week_plan:
        # 用户未修正，后台自动解析
        background_tasks.add_task(
            run_report_parse_background,
            report.id,
            report_data.this_week_work or "",
            report_data.next_week_plan or ""
        )

    # 注意：不再自动触发 trigger_llm_analysis
    # 汇总统计现在直接使用 report_items 数据，LLM 缓存仅作为历史数据的降级方案

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

    # 保存解析结果：优先使用用户修正的结果
    if report_data.this_week_items is not None or report_data.next_week_items is not None:
        # 用户提供了修正后的解析结果，直接保存
        await save_user_parsed_items(
            db, report_id,
            report_data.this_week_items,
            report_data.next_week_items
        )
    elif report_data.this_week_work is not None or report_data.next_week_plan is not None:
        # 内容有更新但用户未修正，后台重新解析
        this_week = report_data.this_week_work if report_data.this_week_work is not None else report.this_week_work
        next_week = report_data.next_week_plan if report_data.next_week_plan is not None else report.next_week_plan
        background_tasks.add_task(
            run_report_parse_background,
            report_id,
            this_week or "",
            next_week or ""
        )

    # 注意：不再自动触发 trigger_llm_analysis
    # 汇总统计现在直接使用 report_items 数据

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
