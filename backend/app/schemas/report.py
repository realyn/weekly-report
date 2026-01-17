from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.report import ReportStatus, ItemType

# 文本字段长度限制（防止存储滥用）
MAX_WORK_TEXT_LENGTH = 10000  # 10KB，足够详细描述工作内容


# ==================== ReportItem Schemas ====================

class ReportItemBase(BaseModel):
    """工作条目基础 Schema"""
    item_type: ItemType
    project_name: Optional[str] = Field(None, max_length=100)
    content: str = Field(..., min_length=1, max_length=2000)
    sequence: int = Field(default=0, ge=0)


class ReportItemCreate(ReportItemBase):
    """创建工作条目"""
    pass


class ReportItemResponse(ReportItemBase):
    """工作条目响应"""
    id: int
    report_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Report Schemas ====================

class ReportBase(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    week_num: int = Field(..., ge=1, le=53)
    this_week_work: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    next_week_plan: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)


class ParsedItemInput(BaseModel):
    """用户修正后的解析条目"""
    project_name: Optional[str] = None
    content: str


class ReportCreate(ReportBase):
    status: Optional[ReportStatus] = ReportStatus.draft
    # 可选：用户修正后的解析结果（如果提供则直接使用，不再自动解析）
    this_week_items: Optional[list[ParsedItemInput]] = None
    next_week_items: Optional[list[ParsedItemInput]] = None


class ReportUpdate(BaseModel):
    this_week_work: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    next_week_plan: Optional[str] = Field(None, max_length=MAX_WORK_TEXT_LENGTH)
    status: Optional[ReportStatus] = None
    # 可选：用户修正后的解析结果
    this_week_items: Optional[list[ParsedItemInput]] = None
    next_week_items: Optional[list[ParsedItemInput]] = None


class ReportResponse(ReportBase):
    id: int
    user_id: int
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    items: list[ReportItemResponse] = []

    class Config:
        from_attributes = True


class ReportWithUser(ReportResponse):
    user_name: str
    department: str


# ==================== 解析相关 Schemas ====================

class ParsedWorkItem(BaseModel):
    """LLM 解析出的单条工作"""
    project_name: Optional[str] = None
    content: str


class ParseResult(BaseModel):
    """解析结果"""
    this_week_items: list[ParsedWorkItem] = []
    next_week_items: list[ParsedWorkItem] = []
    raw_this_week: Optional[str] = None
    raw_next_week: Optional[str] = None


class ParsePreviewRequest(BaseModel):
    """解析预览请求"""
    this_week_work: Optional[str] = None
    next_week_plan: Optional[str] = None
