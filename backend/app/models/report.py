from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class ReportStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"


class ItemType(str, enum.Enum):
    this_week = "this_week"
    next_week = "next_week"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    week_num = Column(Integer, nullable=False)
    this_week_work = Column(Text)
    next_week_plan = Column(Text)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.draft)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="reports")
    items = relationship("ReportItem", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "year", "week_num", name="uk_user_week"),
    )


class ReportItem(Base):
    """
    周报工作条目 - 结构化存储解析后的工作内容
    """
    __tablename__ = "report_items"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(SQLEnum(ItemType), nullable=False)  # 'this_week' 或 'next_week'
    project_name = Column(String(100), nullable=True)  # 项目名称，可为空（通用工作）
    content = Column(Text, nullable=False)  # 工作内容
    sequence = Column(Integer, default=0)  # 排序序号
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    report = relationship("Report", back_populates="items")

    __table_args__ = (
        Index("idx_report_items_report_id", "report_id"),
        Index("idx_report_items_project", "project_name"),
    )
