from datetime import datetime, timedelta


def get_current_week() -> tuple[int, int]:
    """返回当前年份和周数"""
    now = datetime.now()
    return now.year, now.isocalendar()[1]


def get_week_date_range(year: int, week_num: int) -> tuple[str, str]:
    """返回指定周的日期范围"""
    first_day = datetime.strptime(f"{year}-W{week_num:02d}-1", "%Y-W%W-%w")
    last_day = first_day + timedelta(days=6)
    return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")


def get_week_start_date(year: int, week_num: int) -> datetime:
    """获取指定周的周一日期"""
    return datetime.strptime(f"{year}-W{week_num:02d}-1", "%Y-W%W-%w")
