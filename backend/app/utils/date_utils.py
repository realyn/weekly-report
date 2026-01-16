from datetime import datetime, timedelta, date


def get_current_week() -> tuple[int, int]:
    """返回当前年份和周数"""
    now = datetime.now()
    return now.year, now.isocalendar()[1]


def get_week_date_range(year: int, week_num: int) -> tuple[str, str]:
    """返回指定ISO周的日期范围"""
    # 使用 %G (ISO年), %V (ISO周), %u (ISO星期几，1=周一) 格式
    first_day = datetime.strptime(f"{year}-W{week_num:02d}-1", "%G-W%V-%u")
    last_day = first_day + timedelta(days=6)
    return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")


def get_week_start_date(year: int, week_num: int) -> datetime:
    """获取指定ISO周的周一日期"""
    return datetime.strptime(f"{year}-W{week_num:02d}-1", "%G-W%V-%u")


def get_week_end_date(year: int, week_num: int) -> datetime:
    """获取指定ISO周的周日日期"""
    return get_week_start_date(year, week_num) + timedelta(days=6)


async def get_week_deadline(year: int, week_num: int) -> datetime:
    """
    获取指定周的周报修改截止时间
    规则：该周最后一个工作日的 23:59:59
    使用数据库缓存的节假日数据，自动处理法定假日和调休
    """
    from app.services.holiday_service import get_week_deadline as holiday_get_deadline

    return await holiday_get_deadline(year, week_num)


async def is_within_deadline(year: int, week_num: int) -> bool:
    """判断当前时间是否在指定周的截止时间之前"""
    deadline = await get_week_deadline(year, week_num)
    return datetime.now() <= deadline


async def get_deadline_info(year: int, week_num: int) -> dict:
    """
    获取截止时间详细信息
    返回: {
        "deadline": datetime,
        "deadline_str": "1月17日(周五) 23:59",
        "is_expired": bool,
        "remaining": "还剩2天3小时" or "已过期"
    }
    """
    deadline = await get_week_deadline(year, week_num)
    now = datetime.now()
    is_expired = now > deadline

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    deadline_str = f"{deadline.month}月{deadline.day}日({weekday_names[deadline.weekday()]}) 23:59"

    if is_expired:
        remaining = "已过期"
    else:
        diff = deadline - now
        days = diff.days
        hours = diff.seconds // 3600
        if days > 0:
            remaining = f"还剩{days}天{hours}小时"
        elif hours > 0:
            remaining = f"还剩{hours}小时"
        else:
            minutes = (diff.seconds % 3600) // 60
            remaining = f"还剩{minutes}分钟"

    return {
        "deadline": deadline,
        "deadline_str": deadline_str,
        "is_expired": is_expired,
        "remaining": remaining
    }
