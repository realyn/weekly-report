from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

# 文本字段长度限制
MAX_WORK_TEXT_LENGTH = 5000  # 日报内容相对周报更简短


# ==================== DailyReportItem Schemas ====================

class DailyReportItemBase(BaseModel):
    """日报工作条目基础 Schema"""
    task_id: Optional[int] = None  # 关联任务（可选）
    project_name: Optional[str] = Field(None, max_length=100)
    content: str = Field(..., min_length=1, max_length=1000)
    hours: Optional[Decimal] = Field(None, ge=0, le=12)
    progress: Optional[int] = Field(None, ge=0, le=100)  # 进度百分比
    task_progress: Optional[int] = Field(None, ge=0, le=100)  # 任务进度更新
    remark: Optional[str] = Field(None, max_length=500)  # 备注
    sequence: int = Field(default=0, ge=0)


class DailyReportItemCreate(DailyReportItemBase):
    """创建日报工作条目"""
    pass


class DailyReportItemResponse(DailyReportItemBase):
    """日报工作条目响应"""
    id: int
    daily_report_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyReportItemUpdate(BaseModel):
    """管理员修改条目"""
    hours: Optional[Decimal] = Field(None, ge=0, le=12)
    progress: Optional[int] = Field(None, ge=0, le=100)
    remark: Optional[str] = Field(None, max_length=500)


# ==================== DailyReport Schemas ====================

class DailyReportBase(BaseModel):
    date: date
    work_content: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)


class DailyReportItemInput(BaseModel):
    """日报条目输入"""
    task_id: Optional[int] = None  # 关联任务（可选）
    project_name: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=1000)
    hours: Optional[Decimal] = Field(None, ge=0, le=12)
    progress: Optional[int] = Field(None, ge=0, le=100)
    task_progress: Optional[int] = Field(None, ge=0, le=100)  # 任务进度更新
    remark: Optional[str] = Field(None, max_length=500)


class DailyReportCreate(DailyReportBase):
    """创建日报"""
    items: Optional[list[DailyReportItemInput]] = None


class DailyReportUpdate(BaseModel):
    """更新日报"""
    work_content: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    items: Optional[list[DailyReportItemInput]] = None


class DailyReportResponse(DailyReportBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    items: list[DailyReportItemResponse] = []
    editable: bool = True  # 是否可编辑（根据截止时间计算）

    class Config:
        from_attributes = True


class DailyReportWithUser(DailyReportResponse):
    """带用户信息的日报（管理员查看）"""
    user_name: str
    department: str


# ==================== 解析相关 Schemas ====================

class ParsedDailyWorkItem(BaseModel):
    """LLM 解析出的单条工作"""
    project_name: Optional[str] = None
    content: str
    hours: Optional[Decimal] = None


class DailyParseResult(BaseModel):
    """日报解析结果"""
    items: list[ParsedDailyWorkItem] = []
    raw_content: Optional[str] = None


class DailyParsePreviewRequest(BaseModel):
    """日报解析预览请求"""
    work_content: Optional[str] = None


# ==================== 汇总相关 Schemas ====================

class WeekDailySummary(BaseModel):
    """本周日报汇总（用于生成周报）"""
    year: int
    week_num: int
    daily_reports: list[DailyReportResponse] = []
    summary_by_project: dict[str, list[str]] = {}  # 按项目汇总的工作内容
    total_hours_by_project: dict[str, float] = {}  # 按项目汇总的工时


class DailyReportDeadlineInfo(BaseModel):
    """日报截止时间信息"""
    report_date: date
    deadline: datetime
    is_editable: bool
    reason: Optional[str] = None
