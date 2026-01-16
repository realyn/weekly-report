"""
节假日服务 - 自动获取、数据库缓存、智能计算
数据源: apihubs.cn (完整全年数据)
更新策略: 11月15日 + 1月1日自动检查更新
"""
import httpx
from datetime import datetime, date, timedelta
from typing import Optional
import logging
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# API配置
APIHUBS_API = "https://api.apihubs.cn/holiday/get"

# 内存缓存（数据库数据的快速访问层）
_year_cache: dict[int, dict[date, dict]] = {}
_cache_loaded_at: dict[int, datetime] = {}


def _local_fallback(query_date: date) -> dict:
    """本地fallback：简单判断周末"""
    weekday = query_date.weekday()  # 0=周一, 6=周日
    is_weekend = weekday >= 5

    return {
        "date": query_date,
        "is_workday": not is_weekend,
        "day_type": "weekend" if is_weekend else "workday",
        "holiday_name": None
    }


def clear_cache():
    """清除内存缓存"""
    global _year_cache, _cache_loaded_at
    _year_cache = {}
    _cache_loaded_at = {}


# ==================== 数据库持久化层 ====================

async def fetch_year_data_from_api(year: int) -> list[dict]:
    """从API获取全年节假日数据"""
    result = []

    async with httpx.AsyncClient(timeout=30) as client:
        # 尝试 apihubs (完整数据)
        try:
            days_in_year = 366 if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0 else 365
            resp = await client.get(f"{APIHUBS_API}?year={year}&cn=1&size={days_in_year}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    for item in data.get("data", {}).get("list", []):
                        try:
                            date_str = str(item.get("date", ""))
                            d = datetime.strptime(date_str, "%Y%m%d").date()

                            # workday: 1=工作日, 2=休息日
                            workday_flag = item.get("workday", 1)
                            holiday_name = item.get("holiday_cn", "")
                            is_holiday_name = holiday_name and holiday_name != "非节假日"

                            # 判断日期类型
                            if workday_flag == 2:
                                # 休息日：可能是周末或法定假日
                                if is_holiday_name:
                                    day_type = "holiday"
                                else:
                                    day_type = "weekend"
                                is_workday = False
                            else:
                                # 工作日：可能是正常工作日或调休上班
                                weekday = d.weekday()  # 0=周一, 6=周日
                                if weekday >= 5:
                                    # 周末但要上班 = 调休
                                    day_type = "workday_shift"
                                else:
                                    day_type = "workday"
                                is_workday = True

                            result.append({
                                "date": d,
                                "year": d.year,
                                "day_type": day_type,
                                "is_workday": is_workday,
                                "holiday_name": holiday_name if day_type == "holiday" else None
                            })
                        except Exception as e:
                            logger.warning(f"解析apihubs数据项失败: {e}")

                    if result:
                        logger.info(f"从apihubs获取{year}年数据: {len(result)}条")
                        return result
        except Exception as e:
            logger.warning(f"apihubs API失败: {e}")

    logger.error(f"获取{year}年节假日数据失败")
    return result


async def sync_year_to_db(db: AsyncSession, year: int, force: bool = False) -> dict:
    """同步指定年份数据到数据库"""
    from app.models.holiday import HolidayDate, HolidayConfig

    # 检查是否已有数据
    config_result = await db.execute(
        select(HolidayConfig).where(HolidayConfig.year == year)
    )
    config = config_result.scalar_one_or_none()

    if config and config.status == "fetched" and not force:
        return {"status": "exists", "message": f"{year}年数据已存在", "count": config.total_days}

    # 获取数据
    data = await fetch_year_data_from_api(year)
    if not data:
        return {"status": "error", "message": f"获取{year}年数据失败"}

    # 清除旧数据
    await db.execute(delete(HolidayDate).where(HolidayDate.year == year))

    # 插入新数据
    for item in data:
        holiday = HolidayDate(
            date=item["date"],
            year=item["year"],
            day_type=item["day_type"],
            is_workday=item["is_workday"],
            holiday_name=item.get("holiday_name"),
            source="apihubs"
        )
        db.add(holiday)

    # 更新配置
    if not config:
        config = HolidayConfig(year=year)
        db.add(config)

    config.status = "fetched"
    config.source = "apihubs"
    config.fetched_at = datetime.now()
    config.total_days = len(data)

    await db.commit()

    # 清除内存缓存
    if year in _year_cache:
        del _year_cache[year]

    return {"status": "success", "message": f"同步{year}年数据成功", "count": len(data)}


async def load_year_to_memory(db: AsyncSession, year: int) -> dict[date, dict]:
    """从数据库加载年份数据到内存"""
    from app.models.holiday import HolidayDate

    if year in _year_cache:
        # 检查缓存是否过期（1小时）
        if year in _cache_loaded_at:
            if (datetime.now() - _cache_loaded_at[year]).seconds < 3600:
                return _year_cache[year]

    result = await db.execute(
        select(HolidayDate).where(HolidayDate.year == year)
    )
    holidays = result.scalars().all()

    cache = {}
    for h in holidays:
        cache[h.date] = {
            "date": h.date,
            "is_workday": h.is_workday,
            "day_type": h.day_type,
            "holiday_name": h.holiday_name
        }

    if cache:
        _year_cache[year] = cache
        _cache_loaded_at[year] = datetime.now()

    return cache


async def get_date_info_from_db(db: AsyncSession, query_date: date) -> dict:
    """从数据库获取日期信息（带内存缓存）"""
    year = query_date.year
    cache = await load_year_to_memory(db, year)

    if query_date in cache:
        return cache[query_date]

    # 数据库无数据，尝试同步
    if not cache:
        await sync_year_to_db(db, year)
        cache = await load_year_to_memory(db, year)
        if query_date in cache:
            return cache[query_date]

    # 仍无数据，使用本地fallback
    return _local_fallback(query_date)


async def get_week_deadline_smart(db: AsyncSession, year: int, week_num: int) -> datetime:
    """
    智能计算周报截止时间
    规则: 该周最后一个工作日的 23:59:59
    """
    from app.models.holiday import DeadlineOverride

    # 1. 检查手动覆盖
    override_result = await db.execute(
        select(DeadlineOverride)
        .where(DeadlineOverride.year == year)
        .where(DeadlineOverride.week_num == week_num)
    )
    override = override_result.scalar_one_or_none()
    if override:
        return override.deadline

    # 2. 使用 ISO 周标准计算周一
    target_monday = datetime.strptime(f"{year}-W{week_num:02d}-1", "%G-W%V-%u").date()
    target_sunday = target_monday + timedelta(days=6)

    # 3. 从周日往前找最后一个工作日
    deadline_date = target_sunday
    for i in range(7):  # 从周日(6)到周一(0)
        check_date = target_sunday - timedelta(days=i)
        info = await get_date_info_from_db(db, check_date)
        if info.get("is_workday", check_date.weekday() < 5):
            deadline_date = check_date
            break

    return datetime.combine(deadline_date, datetime.max.time().replace(microsecond=0))


async def init_holiday_data():
    """初始化节假日数据（启动时调用）"""
    from app.database import async_session

    current_year = datetime.now().year
    years_to_load = [current_year, current_year + 1]

    async with async_session() as db:
        for year in years_to_load:
            try:
                result = await sync_year_to_db(db, year)
                logger.info(f"初始化节假日数据: {year}年 - {result.get('message')}")
            except Exception as e:
                logger.error(f"初始化{year}年节假日数据失败: {e}")


# ==================== 便捷包装函数 ====================

async def get_week_deadline(year: int, week_num: int) -> datetime:
    """
    获取指定周的截止时间（自动创建db session）
    供 date_utils.py 调用
    """
    from app.database import async_session

    async with async_session() as db:
        return await get_week_deadline_smart(db, year, week_num)


async def is_workday(query_date: date) -> bool:
    """判断指定日期是否为工作日"""
    from app.database import async_session

    async with async_session() as db:
        info = await get_date_info_from_db(db, query_date)
        return info.get("is_workday", query_date.weekday() < 5)


async def check_and_update_holiday_data():
    """
    检查并更新节假日数据
    定时任务调用：11月15日更新下一年，1月1日更新当年
    """
    from app.database import async_session

    now = datetime.now()
    current_year = now.year

    async with async_session() as db:
        # 11月15日后：检查下一年数据
        if now.month >= 11 and now.day >= 15:
            next_year = current_year + 1
            result = await sync_year_to_db(db, next_year)
            logger.info(f"定时更新检查: {next_year}年 - {result.get('message')}")

        # 1月1日后：强制刷新当年数据
        if now.month == 1 and now.day <= 7:
            result = await sync_year_to_db(db, current_year, force=True)
            logger.info(f"定时更新检查: {current_year}年 - {result.get('message')}")
