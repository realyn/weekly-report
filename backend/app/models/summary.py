from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from datetime import datetime
from app.database import Base


class WeeklySummary(Base):
    __tablename__ = "weekly_summary"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    week_num = Column(Integer, nullable=False)
    summary_data = Column(Text)  # JSON格式
    statistics = Column(Text)  # JSON格式
    llm_analysis = Column(Text)  # LLM分析结果缓存 (JSON)
    doc_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    analyzed_at = Column(DateTime)  # LLM分析时间

    __table_args__ = (
        UniqueConstraint("year", "week_num", name="uk_year_week"),
    )
