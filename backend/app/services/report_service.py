from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate


async def get_report_by_id(db: AsyncSession, report_id: int) -> Optional[Report]:
    result = await db.execute(select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()


async def get_user_report(db: AsyncSession, user_id: int, year: int, week_num: int) -> Optional[Report]:
    result = await db.execute(
        select(Report).where(
            Report.user_id == user_id,
            Report.year == year,
            Report.week_num == week_num
        )
    )
    return result.scalar_one_or_none()


async def get_reports(db: AsyncSession, year: int, week_num: Optional[int] = None, user_id: Optional[int] = None):
    query = select(Report).where(Report.year == year)
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


async def get_week_reports_with_users(db: AsyncSession, year: int, week_num: int):
    result = await db.execute(
        select(Report, User).join(User).where(
            Report.year == year,
            Report.week_num == week_num,
            Report.status == "submitted"
        )
    )
    return result.all()
