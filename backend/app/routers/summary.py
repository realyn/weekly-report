from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import os
from app.database import get_db
from app.services.summary_service import get_weekly_summary, save_weekly_summary
from app.services.word_generator import generate_weekly_word
from app.utils.security import get_current_user
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
    summary = await get_weekly_summary(db, year, week)
    return {"code": 200, "data": summary}


@router.get("/download/{year}/{week}")
async def download_word(
    year: int,
    week: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    summary = await get_weekly_summary(db, year, week)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not year:
        year, _ = get_current_week()
    # TODO: 实现图表数据统计
    return {"code": 200, "data": {"year": year, "weekly_stats": []}}
