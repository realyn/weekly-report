from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import logging

from app.database import get_db, async_session
from app.schemas.daily_report import (
    DailyReportCreate, DailyReportUpdate, DailyReportResponse,
    DailyReportWithUser, DailyParseResult, DailyParsePreviewRequest,
    WeekDailySummary, DailyReportDeadlineInfo, DailyReportItemUpdate
)
from app.services import daily_report_service
from app.services.report_parser_service import get_report_parser_service
from app.utils.security import get_current_user, get_current_admin
from app.utils.date_utils import get_current_week
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/daily-reports", tags=["日报"])
logger = logging.getLogger(__name__)


def build_response(report, editable: bool = None) -> DailyReportResponse:
    """构建日报响应"""
    if editable is None:
        editable = daily_report_service.is_editable(report.date)
    return DailyReportResponse(
        id=report.id,
        user_id=report.user_id,
        date=report.date,
        work_content=report.work_content,
        created_at=report.created_at,
        updated_at=report.updated_at,
        items=[item for item in report.items],
        editable=editable
    )


@router.get("/current", response_model=Optional[DailyReportResponse])
async def get_current_daily_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取今日日报"""
    today = date.today()
    report = await daily_report_service.get_user_daily_report(db, current_user.id, today)
    if report:
        return build_response(report, editable=True)
    return None


@router.get("/deadline")
async def get_deadline_info(
    report_date: date,
    current_user: User = Depends(get_current_user)
) -> DailyReportDeadlineInfo:
    """获取日报截止时间信息"""
    deadline = daily_report_service.get_edit_deadline(report_date)
    editable = daily_report_service.is_editable(report_date)

    reason = None
    if not editable:
        reason = "已超过修改截止时间（次日中午12点）且不在本工作周内"

    return DailyReportDeadlineInfo(
        report_date=report_date,
        deadline=deadline,
        is_editable=editable,
        reason=reason
    )


@router.post("/parse-preview", response_model=DailyParseResult)
async def parse_preview(
    request: DailyParsePreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """解析日报内容预览"""
    if not request.work_content:
        return DailyParseResult(items=[], raw_content=None)

    parser = get_report_parser_service()
    # 复用周报解析，只传本周工作
    parse_result = await parser.parse_report_text(request.work_content, None)

    # 转换为日报格式
    return DailyParseResult(
        items=[
            {"project_name": item.project_name, "content": item.content, "hours": None}
            for item in parse_result.this_week_items
        ],
        raw_content=request.work_content
    )


@router.get("/week-summary", response_model=WeekDailySummary)
async def get_week_summary(
    year: Optional[int] = None,
    week_num: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取本周日报汇总（用于生成周报）"""
    if year is None or week_num is None:
        current_year, current_week = get_current_week()
        year = year or current_year
        week_num = week_num or current_week

    daily_reports = await daily_report_service.get_week_daily_reports(
        db, current_user.id, year, week_num
    )

    summary = await daily_report_service.get_week_summary_by_project(
        db, current_user.id, year, week_num
    )

    return WeekDailySummary(
        year=year,
        week_num=week_num,
        daily_reports=[build_response(r) for r in daily_reports],
        summary_by_project=summary["summary_by_project"],
        total_hours_by_project=summary["total_hours_by_project"]
    )


@router.get("/", response_model=list[DailyReportResponse])
async def get_daily_reports(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的日报列表"""
    reports = await daily_report_service.get_daily_reports(
        db, user_id=current_user.id, start_date=start_date, end_date=end_date
    )
    return [build_response(r) for r in reports]


@router.get("/{report_id}", response_model=DailyReportResponse)
async def get_daily_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个日报"""
    report = await daily_report_service.get_daily_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")

    # 检查权限：本人或管理员
    if report.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="无权查看该日报")

    return build_response(report)


@router.post("/", response_model=DailyReportResponse)
async def create_daily_report(
    report_data: DailyReportCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建日报"""
    # 检查是否已存在
    existing = await daily_report_service.get_user_daily_report(
        db, current_user.id, report_data.date
    )
    if existing:
        raise HTTPException(status_code=400, detail="该日期已有日报，请使用更新接口")

    # 检查日期有效性（不能填写未来日期）
    if report_data.date > date.today():
        raise HTTPException(status_code=400, detail="不能填写未来日期的日报")

    # 检查是否可编辑
    if not daily_report_service.is_editable(report_data.date):
        raise HTTPException(status_code=400, detail="该日期已超过可填写时间")

    # 创建日报
    report = await daily_report_service.create_daily_report(db, current_user.id, report_data)

    # 保存解析结果
    if report_data.items:
        report = await daily_report_service.save_daily_report_items(db, report, report_data.items)
    elif report_data.work_content:
        # 后台异步解析
        background_tasks.add_task(
            run_daily_report_parse_background,
            report.id,
            report_data.work_content
        )

    return build_response(report, editable=True)


@router.put("/{report_id}", response_model=DailyReportResponse)
async def update_daily_report(
    report_id: int,
    report_data: DailyReportUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新日报"""
    report = await daily_report_service.get_daily_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")

    # 检查权限
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改该日报")

    # 检查是否可编辑
    if not daily_report_service.is_editable(report.date):
        raise HTTPException(status_code=400, detail="该日报已超过可修改时间")

    # 更新日报
    report = await daily_report_service.update_daily_report(db, report, report_data)

    # 保存解析结果
    if report_data.items is not None:
        report = await daily_report_service.save_daily_report_items(db, report, report_data.items)
    elif report_data.work_content:
        # 后台异步解析
        background_tasks.add_task(
            run_daily_report_parse_background,
            report.id,
            report_data.work_content
        )

    return build_response(report)


@router.delete("/{report_id}")
async def delete_daily_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除日报"""
    report = await daily_report_service.get_daily_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")

    # 检查权限
    if report.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="无权删除该日报")

    # 检查是否可编辑（普通用户）
    if current_user.role != UserRole.admin and not daily_report_service.is_editable(report.date):
        raise HTTPException(status_code=400, detail="该日报已超过可删除时间")

    await daily_report_service.delete_daily_report(db, report)
    return {"message": "日报已删除"}


# ==================== 管理员接口 ====================

@router.get("/admin/list", response_model=list[DailyReportWithUser])
async def admin_get_daily_reports(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员获取所有用户日报"""
    results = await daily_report_service.get_daily_reports_with_users(
        db, start_date=start_date, end_date=end_date
    )

    return [
        DailyReportWithUser(
            id=report.id,
            user_id=report.user_id,
            date=report.date,
            work_content=report.work_content,
            created_at=report.created_at,
            updated_at=report.updated_at,
            items=[item for item in report.items],
            editable=daily_report_service.is_editable(report.date),
            user_name=user.real_name,
            department=user.department
        )
        for report, user in results
    ]


@router.put("/admin/item/{item_id}/hours")
async def admin_update_item_hours(
    item_id: int,
    update_data: DailyReportItemUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """管理员修改工时"""
    if update_data.hours is None:
        raise HTTPException(status_code=400, detail="工时不能为空")

    item = await daily_report_service.update_item_hours(db, item_id, update_data.hours)
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")

    return {"message": "工时已更新", "hours": float(item.hours)}


# ==================== 后台任务 ====================

async def run_daily_report_parse_background(report_id: int, work_content: str):
    """后台解析日报内容"""
    try:
        parser = get_report_parser_service()
        async with async_session() as db:
            report = await daily_report_service.get_daily_report_by_id(db, report_id)
            if report:
                # 复用周报解析
                parse_result = await parser.parse_report_text(work_content, None)
                # 转换为日报格式
                from app.schemas.daily_report import DailyReportItemInput
                items = [
                    DailyReportItemInput(
                        project_name=item.project_name,
                        content=item.content,
                        hours=None,
                        progress=None,
                        remark=None
                    )
                    for item in parse_result.this_week_items
                ]
                await daily_report_service.save_daily_report_items(db, report, items)
    except Exception:
        logger.exception(f"后台日报解析失败: report_id={report_id}")
