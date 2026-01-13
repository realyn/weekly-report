from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import json
from app.models.report import Report
from app.models.user import User
from app.models.summary import WeeklySummary
from app.utils.date_utils import get_week_date_range


async def get_weekly_summary(db: AsyncSession, year: int, week_num: int) -> dict:
    """获取周汇总数据"""
    # 获取日期范围
    start_date, end_date = get_week_date_range(year, week_num)

    # 查询所有已提交的周报
    result = await db.execute(
        select(Report, User)
        .join(User)
        .where(
            Report.year == year,
            Report.week_num == week_num,
            Report.status == "submitted"
        )
        .order_by(User.real_name)
    )
    reports_with_users = result.all()

    # 统计数据
    total_members = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    submitted_count = len(reports_with_users)

    reports_data = []
    total_tasks = 0
    for report, user in reports_with_users:
        # 计算任务数（按换行或数字开头计算）
        task_count = len([l for l in (report.this_week_work or "").split("\n") if l.strip()])
        total_tasks += task_count
        reports_data.append({
            "user_id": user.id,
            "user_name": user.real_name,
            "department": user.department,
            "this_week_work": report.this_week_work,
            "next_week_plan": report.next_week_plan,
            "task_count": task_count
        })

    return {
        "year": year,
        "week_num": week_num,
        "date_range": f"{start_date} ~ {end_date}",
        "total_members": total_members,
        "submitted_count": submitted_count,
        "submission_rate": round(submitted_count / total_members * 100, 1) if total_members else 0,
        "reports": reports_data,
        "statistics": {
            "total_tasks": total_tasks
        }
    }


async def save_weekly_summary(db: AsyncSession, year: int, week_num: int, summary_data: dict, doc_path: Optional[str] = None):
    """保存周汇总"""
    result = await db.execute(
        select(WeeklySummary).where(
            WeeklySummary.year == year,
            WeeklySummary.week_num == week_num
        )
    )
    summary = result.scalar_one_or_none()

    if summary:
        summary.summary_data = json.dumps(summary_data, ensure_ascii=False)
        if doc_path:
            summary.doc_path = doc_path
    else:
        summary = WeeklySummary(
            year=year,
            week_num=week_num,
            summary_data=json.dumps(summary_data, ensure_ascii=False),
            doc_path=doc_path
        )
        db.add(summary)

    await db.commit()
    return summary
