"""节假日数据模型"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, UniqueConstraint
from datetime import datetime
from app.database import Base


class HolidayDate(Base):
    """节假日数据表 - 存储每天的工作/休息状态"""
    __tablename__ = "holiday_dates"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    year = Column(Integer, nullable=False, index=True)

    # 日期类型: workday(工作日), weekend(周末), holiday(法定假日), workday_shift(调休上班)
    day_type = Column(String(20), nullable=False)

    # 是否需要上班
    is_workday = Column(Boolean, nullable=False)

    # 节日名称（如"春节"、"国庆节"），普通日期为空
    holiday_name = Column(String(50), nullable=True)

    # 数据来源
    source = Column(String(50), default="api")

    # 更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class HolidayConfig(Base):
    """节假日配置表 - 存储数据更新状态和自定义覆盖"""
    __tablename__ = "holiday_configs"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, unique=True)

    # 数据状态: pending(待获取), fetched(已获取), verified(已验证)
    status = Column(String(20), default="pending")

    # 数据来源和获取时间
    source = Column(String(50), nullable=True)
    fetched_at = Column(DateTime, nullable=True)

    # 数据条数
    total_days = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DeadlineOverride(Base):
    """截止时间自定义覆盖表 - 管理员手动设置"""
    __tablename__ = "deadline_overrides"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    week_num = Column(Integer, nullable=False)

    # 自定义截止时间
    deadline = Column(DateTime, nullable=False)

    # 原因说明
    reason = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('year', 'week_num', name='uix_year_week'),
    )
