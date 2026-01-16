from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.report import ReportStatus

# 文本字段长度限制（防止存储滥用）
MAX_WORK_TEXT_LENGTH = 10000  # 10KB，足够详细描述工作内容


class ReportBase(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    week_num: int = Field(..., ge=1, le=53)
    this_week_work: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    next_week_plan: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)


class ReportCreate(ReportBase):
    status: Optional[ReportStatus] = ReportStatus.draft


class ReportUpdate(BaseModel):
    this_week_work: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    next_week_plan: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    status: Optional[ReportStatus] = None


class ReportResponse(ReportBase):
    id: int
    user_id: int
    status: ReportStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportWithUser(ReportResponse):
    user_name: str
    department: str
