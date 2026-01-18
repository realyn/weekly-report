from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, UniqueConstraint, Index, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class DailyReport(Base):
    """
    日报主表 - 每人每天一份
    """
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)  # 日报日期
    work_content = Column(Text)  # 今日工作原始文本
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="daily_reports")
    items = relationship("DailyReportItem", back_populates="daily_report", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uk_user_date"),
        Index("idx_daily_reports_date", "date"),
    )


class DailyReportItem(Base):
    """
    日报工作条目 - 结构化存储工作内容
    """
    __tablename__ = "daily_report_items"

    id = Column(Integer, primary_key=True, index=True)
    daily_report_id = Column(Integer, ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)  # 关联任务（可选）
    project_name = Column(String(100), nullable=True)  # 项目名称，可为空（通用工作）
    content = Column(Text, nullable=False)  # 工作内容
    hours = Column(Numeric(3, 1), nullable=True)  # 工时（0.5-12小时）
    progress = Column(Integer, nullable=True)  # 进度百分比（0-100）
    task_progress = Column(Integer, nullable=True)  # 任务进度更新（0-100）
    remark = Column(Text, nullable=True)  # 备注
    sequence = Column(Integer, default=0)  # 排序序号
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    daily_report = relationship("DailyReport", back_populates="items")

    __table_args__ = (
        Index("idx_daily_report_items_report_id", "daily_report_id"),
        Index("idx_daily_report_items_project", "project_name"),
        Index("idx_daily_report_items_task", "task_id"),
    )
