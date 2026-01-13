from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class ReportStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"


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

    __table_args__ = (
        UniqueConstraint("user_id", "year", "week_num", name="uk_user_week"),
    )
