from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.report import ReportStatus


class ReportBase(BaseModel):
    year: int
    week_num: int
    this_week_work: Optional[str] = None
    next_week_plan: Optional[str] = None


class ReportCreate(ReportBase):
    status: Optional[ReportStatus] = ReportStatus.draft


class ReportUpdate(BaseModel):
    this_week_work: Optional[str] = None
    next_week_plan: Optional[str] = None
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
