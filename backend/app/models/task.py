from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Task(Base):
    """
    任务主表 - 支持跨天进度追踪
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)  # 任务标题
    description = Column(Text, nullable=True)  # 任务描述
    project_name = Column(String(100), nullable=True)  # 关联项目名称

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 创建者
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 负责人（可选）

    status = Column(String(20), default="pending")  # pending/in_progress/completed/cancelled
    priority = Column(Integer, default=0)  # 优先级 0-3
    progress = Column(Integer, default=0)  # 进度 0-100

    start_date = Column(Date, nullable=True)  # 开始日期
    due_date = Column(Date, nullable=True)  # 截止日期
    completed_at = Column(DateTime, nullable=True)  # 完成时间

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    creator = relationship("User", foreign_keys=[creator_id], backref="created_tasks")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_tasks")
    progress_logs = relationship("TaskProgressLog", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tasks_creator", "creator_id"),
        Index("idx_tasks_assignee", "assignee_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_project", "project_name"),
    )


class TaskProgressLog(Base):
    """
    任务进度日志 - 记录每次进度变更
    """
    __tablename__ = "task_progress_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    daily_report_item_id = Column(Integer, ForeignKey("daily_report_items.id", ondelete="SET NULL"), nullable=True)

    date = Column(Date, nullable=False)  # 记录日期
    progress_before = Column(Integer, nullable=True)  # 更新前进度
    progress_after = Column(Integer, nullable=True)  # 更新后进度
    content = Column(Text, nullable=True)  # 当日工作内容

    created_at = Column(DateTime, default=datetime.now)

    # 关系
    task = relationship("Task", back_populates="progress_logs")

    __table_args__ = (
        Index("idx_task_progress_logs_task", "task_id"),
        Index("idx_task_progress_logs_date", "date"),
    )
