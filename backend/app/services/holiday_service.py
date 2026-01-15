"""
节假日API服务
主要源: timor.tech
备选源: holiday.ailcc.com
"""
import httpx
from datetime import datetime, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# API配置
TIMOR_API = "https://timor.tech/api/holiday"
AILCC_API = "https://holiday.ailcc.com/api/holiday"

# 缓存（简单内存缓存，避免频繁请求）
_cache: dict[str, dict] = {}
_cache_ttl = 3600  # 1小时缓存


async def get_date_info(query_date: date) -> dict:
    """
    获取指定日期的节假日信息

    返回格式:
    {
        "date": "2026-01-19",
        "is_workday": True/False,  # 是否工作日（需上班）
        "type": 0/1/2/3,           # 0工作日 1周末 2节日 3调休
        "type_name": "工作日/周末/节日/调休",
        "holiday_name": "春节" or None
    }
    """
    date_str = query_date.strftime("%Y-%m-%d")

    # 检查缓存
    cache_key = f"date_{date_str}"
    if cache_key in _cache:
        cached = _cache[cache_key]
        if datetime.now().timestamp() - cached.get("_ts", 0) < _cache_ttl:
            return cached

    # 尝试主要源
    result = await _fetch_from_timor(date_str)

    # 主要源失败，尝试备选源
    if result is None:
        logger.warning(f"timor.tech API failed for {date_str}, trying ailcc...")
        result = await _fetch_from_ailcc(date_str)

    # 都失败，使用本地fallback（简单判断周末）
    if result is None:
        logger.warning(f"All holiday APIs failed for {date_str}, using local fallback")
        result = _local_fallback(query_date)

    # 缓存结果
    result["_ts"] = datetime.now().timestamp()
    _cache[cache_key] = result

    return result


async def _fetch_from_timor(date_str: str) -> Optional[dict]:
    """从 timor.tech 获取节假日信息"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{TIMOR_API}/info/{date_str}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    type_info = data.get("type", {})
                    type_code = type_info.get("type", 0)
                    holiday = data.get("holiday")

                    return {
                        "date": date_str,
                        "is_workday": type_code in (0, 3),  # 0工作日 3调休（需上班）
                        "type": type_code,
                        "type_name": type_info.get("name", ""),
                        "holiday_name": holiday.get("name") if holiday else None
                    }
    except Exception as e:
        logger.error(f"timor.tech API error: {e}")
    return None


async def _fetch_from_ailcc(date_str: str) -> Optional[dict]:
    """从 holiday.ailcc.com 获取节假日信息"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{AILCC_API}/info/{date_str}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    info = data.get("data", {})
                    type_code = info.get("type", 0)

                    type_names = {0: "工作日", 1: "周末", 2: "节日", 3: "调休"}

                    return {
                        "date": date_str,
                        "is_workday": type_code in (0, 3),
                        "type": type_code,
                        "type_name": type_names.get(type_code, ""),
                        "holiday_name": info.get("name")
                    }
    except Exception as e:
        logger.error(f"ailcc API error: {e}")
    return None


def _local_fallback(query_date: date) -> dict:
    """本地fallback：简单判断周末"""
    weekday = query_date.weekday()  # 0=周一, 6=周日
    is_weekend = weekday >= 5

    return {
        "date": query_date.strftime("%Y-%m-%d"),
        "is_workday": not is_weekend,
        "type": 1 if is_weekend else 0,
        "type_name": "周末" if is_weekend else "工作日",
        "holiday_name": None
    }


async def is_workday(query_date: date) -> bool:
    """判断指定日期是否为工作日"""
    info = await get_date_info(query_date)
    return info.get("is_workday", True)


async def get_week_last_workday(year: int, week_num: int) -> date:
    """
    获取指定ISO周的最后一个工作日
    从周日往前找，找到第一个工作日
    """
    from app.utils.date_utils import get_week_start_date

    monday = get_week_start_date(year, week_num)
    sunday = monday + __import__("datetime").timedelta(days=6)

    # 从周日往周一方向找最后一个工作日
    current = sunday
    while current >= monday:
        if await is_workday(current.date() if hasattr(current, 'date') else current):
            return current.date() if hasattr(current, 'date') else current
        current -= __import__("datetime").timedelta(days=1)

    # 如果整周都不是工作日（极端情况），返回周五
    return (monday + __import__("datetime").timedelta(days=4)).date()


def clear_cache():
    """清除缓存"""
    global _cache
    _cache = {}
