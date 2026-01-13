from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import async_session
from app.services.summary_service import get_weekly_summary, save_weekly_summary
from app.services.word_generator import generate_weekly_word
from app.utils.date_utils import get_current_week
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def weekly_summary_job():
    """每周六自动汇总"""
    logger.info("开始执行周报汇总任务")
    year, week_num = get_current_week()

    async with async_session() as db:
        try:
            summary = await get_weekly_summary(db, year, week_num)
            if summary.get("reports"):
                doc_path = generate_weekly_word(summary)
                await save_weekly_summary(db, year, week_num, summary, doc_path)
                logger.info(f"周报汇总完成: {year}年第{week_num}周, 文档: {doc_path}")
            else:
                logger.warning(f"该周没有已提交的周报: {year}年第{week_num}周")
        except Exception as e:
            logger.error(f"周报汇总失败: {e}")


def setup_scheduler():
    """设置定时任务"""
    # 每周六18:00执行汇总
    scheduler.add_job(
        weekly_summary_job,
        CronTrigger(day_of_week="sat", hour=18, minute=0),
        id="weekly_summary",
        replace_existing=True
    )
    return scheduler
