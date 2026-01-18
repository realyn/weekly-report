from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.models.daily_report import DailyReport, DailyReportItem
from app.models.user import User
from app.schemas.daily_report import (
    DailyReportCreate, DailyReportUpdate, DailyReportItemInput, DailyReportItemUpdate
)


def get_edit_deadline(report_date: date) -> datetime:
    """
    获取日报编辑截止时间
    规则：次日中午12点前可修改
    """
    next_day = report_date + timedelta(days=1)
    return datetime.combine(next_day, datetime.min.time().replace(hour=12))


def is_same_work_week(report_date: date, today: date) -> bool:
    """
    判断日报日期是否在当前工作周内
    工作周：周一到周日
    """
    # 获取report_date所在周的周一
    report_monday = report_date - timedelta(days=report_date.weekday())
    # 获取today所在周的周一
    today_monday = today - timedelta(days=today.weekday())
    return report_monday == today_monday


def is_editable(report_date: date) -> bool:
    """
    判断日报是否可编辑
    条件1：次日中午12点前可修改
    条件2：在本工作周内可修改
    """
    now = datetime.now()
    today = now.date()

    # 条件1：截止时间判断
    deadline = get_edit_deadline(report_date)
    if now <= deadline:
        return True

    # 条件2：本工作周内判断
    if is_same_work_week(report_date, today):
        return True

    return False


async def get_daily_report_by_id(db: AsyncSession, report_id: int) -> Optional[DailyReport]:
    """通过ID获取日报"""
    result = await db.execute(
        select(DailyReport)
        .options(selectinload(DailyReport.items))
        .where(DailyReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def get_user_daily_report(db: AsyncSession, user_id: int, report_date: date) -> Optional[DailyReport]:
    """获取用户特定日期的日报"""
    result = await db.execute(
        select(DailyReport)
        .options(selectinload(DailyReport.items))
        .where(
            DailyReport.user_id == user_id,
            DailyReport.date == report_date
        )
    )
    return result.scalar_one_or_none()


async def get_daily_reports(
    db: AsyncSession,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[DailyReport]:
    """获取日报列表"""
    query = select(DailyReport).options(selectinload(DailyReport.items))

    if user_id:
        query = query.where(DailyReport.user_id == user_id)
    if start_date:
        query = query.where(DailyReport.date >= start_date)
    if end_date:
        query = query.where(DailyReport.date <= end_date)

    query = query.order_by(DailyReport.date.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_week_daily_reports(db: AsyncSession, user_id: int, year: int, week_num: int) -> List[DailyReport]:
    """获取用户某周的所有日报"""
    # 计算该周的起止日期（ISO周）
    from datetime import datetime
    jan4 = date(year, 1, 4)
    start_of_year = jan4 - timedelta(days=jan4.weekday())
    week_start = start_of_year + timedelta(weeks=week_num - 1)
    week_end = week_start + timedelta(days=6)

    return await get_daily_reports(db, user_id=user_id, start_date=week_start, end_date=week_end)


async def create_daily_report(db: AsyncSession, user_id: int, report_data: DailyReportCreate) -> DailyReport:
    """创建日报"""
    report = DailyReport(
        user_id=user_id,
        date=report_data.date,
        work_content=report_data.work_content
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def update_daily_report(db: AsyncSession, report: DailyReport, report_data: DailyReportUpdate) -> DailyReport:
    """更新日报"""
    update_data = report_data.model_dump(exclude_unset=True, exclude={'items'})
    for field, value in update_data.items():
        setattr(report, field, value)
    await db.commit()
    await db.refresh(report)
    return report


async def delete_daily_report(db: AsyncSession, report: DailyReport):
    """删除日报"""
    await db.delete(report)
    await db.commit()


async def save_daily_report_items(
    db: AsyncSession,
    report: DailyReport,
    items: List[DailyReportItemInput]
) -> DailyReport:
    """保存日报工作条目（先删后插），并同步任务进度"""
    # 删除旧条目
    await db.execute(
        delete(DailyReportItem).where(DailyReportItem.daily_report_id == report.id)
    )

    # 插入新条目
    for i, item in enumerate(items):
        db_item = DailyReportItem(
            daily_report_id=report.id,
            task_id=item.task_id,
            project_name=item.project_name,
            content=item.content,
            hours=item.hours,
            progress=item.progress,
            task_progress=item.task_progress,
            remark=item.remark,
            sequence=i
        )
        db.add(db_item)

        # 如果关联了任务且有进度更新，同步任务进度
        if item.task_id and item.task_progress is not None:
            await _sync_task_progress(db, item.task_id, item.task_progress, item.content, report.date, db_item)

    await db.commit()

    # 重新加载
    result = await db.execute(
        select(DailyReport)
        .options(selectinload(DailyReport.items))
        .where(DailyReport.id == report.id)
    )
    return result.scalar_one()


async def _sync_task_progress(
    db: AsyncSession,
    task_id: int,
    new_progress: int,
    content: str,
    report_date: date,
    report_item: DailyReportItem
):
    """同步任务进度（内部方法）"""
    from app.models.task import Task, TaskProgressLog
    from datetime import datetime

    # 获取任务
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        return

    progress_before = task.progress

    # 只有新进度大于当前进度时才更新（防止回退）
    if new_progress > task.progress:
        # 记录进度日志
        log = TaskProgressLog(
            task_id=task_id,
            daily_report_item_id=report_item.id,
            date=report_date,
            progress_before=progress_before,
            progress_after=new_progress,
            content=content
        )
        db.add(log)

        # 更新任务进度
        task.progress = new_progress

        # 自动更新任务状态
        if new_progress == 100 and task.status != "completed":
            task.status = "completed"
            task.completed_at = datetime.now()
        elif new_progress > 0 and task.status == "pending":
            task.status = "in_progress"


async def update_item_hours(db: AsyncSession, item_id: int, hours: Decimal) -> Optional[DailyReportItem]:
    """管理员更新工时"""
    result = await db.execute(
        select(DailyReportItem).where(DailyReportItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item:
        item.hours = hours
        await db.commit()
        await db.refresh(item)
    return item


async def get_daily_reports_with_users(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[tuple]:
    """获取日报列表（含用户信息，管理员用）"""
    query = (
        select(DailyReport, User)
        .join(User)
        .options(selectinload(DailyReport.items))
    )

    if start_date:
        query = query.where(DailyReport.date >= start_date)
    if end_date:
        query = query.where(DailyReport.date <= end_date)

    query = query.order_by(DailyReport.date.desc(), User.real_name)
    result = await db.execute(query)
    return list(result.all())


async def get_week_summary_by_project(
    db: AsyncSession,
    user_id: int,
    year: int,
    week_num: int
) -> dict:
    """
    获取某周日报按项目汇总
    用于生成周报
    """
    daily_reports = await get_week_daily_reports(db, user_id, year, week_num)

    summary_by_project: dict[str, list[str]] = {}
    total_hours_by_project: dict[str, float] = {}

    for report in daily_reports:
        for item in report.items:
            project = item.project_name or "其他工作"
            if project not in summary_by_project:
                summary_by_project[project] = []
                total_hours_by_project[project] = 0.0

            # 添加内容（带日期标记）
            date_str = report.date.strftime("%m/%d")
            summary_by_project[project].append(f"[{date_str}] {item.content}")

            # 累加工时
            if item.hours:
                total_hours_by_project[project] += float(item.hours)

    return {
        "summary_by_project": summary_by_project,
        "total_hours_by_project": total_hours_by_project
    }
