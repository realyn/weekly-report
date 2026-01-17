from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct
from sqlalchemy.orm import selectinload
from typing import Optional, List
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate


async def get_report_by_id(db: AsyncSession, report_id: int) -> Optional[Report]:
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.items))
        .where(Report.id == report_id)
    )
    return result.scalar_one_or_none()


async def get_user_report(db: AsyncSession, user_id: int, year: int, week_num: int) -> Optional[Report]:
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.items))
        .where(
            Report.user_id == user_id,
            Report.year == year,
            Report.week_num == week_num
        )
    )
    return result.scalar_one_or_none()


async def get_reports(db: AsyncSession, year: int, week_num: Optional[int] = None, user_id: Optional[int] = None):
    query = select(Report).options(selectinload(Report.items)).where(Report.year == year)
    if week_num:
        query = query.where(Report.week_num == week_num)
    if user_id:
        query = query.where(Report.user_id == user_id)
    result = await db.execute(query.order_by(Report.week_num.desc()))
    return result.scalars().all()


async def create_report(db: AsyncSession, user_id: int, report_data: ReportCreate) -> Report:
    report = Report(user_id=user_id, **report_data.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def update_report(db: AsyncSession, report: Report, report_data: ReportUpdate) -> Report:
    for field, value in report_data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)
    await db.commit()
    await db.refresh(report)
    return report


async def delete_report(db: AsyncSession, report: Report):
    await db.delete(report)
    await db.commit()


async def get_available_years(db: AsyncSession, user_id: Optional[int] = None) -> List[int]:
    """获取有周报记录的年份列表"""
    query = select(distinct(Report.year))
    if user_id:
        query = query.where(Report.user_id == user_id)
    query = query.order_by(Report.year.desc())
    result = await db.execute(query)
    return [row[0] for row in result.fetchall()]


async def get_week_reports_with_users(db: AsyncSession, year: int, week_num: int):
    result = await db.execute(
        select(Report, User).join(User).where(
            Report.year == year,
            Report.week_num == week_num,
            Report.status == "submitted"
        )
    )
    return result.all()
