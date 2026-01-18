from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


# ==================== Task Schemas ====================

class TaskBase(BaseModel):
    """任务基础 Schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    project_name: Optional[str] = Field(None, max_length=100)
    priority: int = Field(default=0, ge=0, le=3)
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    """创建任务"""
    assignee_id: Optional[int] = None  # 可选指定负责人


class TaskUpdate(BaseModel):
    """更新任务"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    project_name: Optional[str] = Field(None, max_length=100)
    assignee_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    priority: Optional[int] = Field(None, ge=0, le=3)
    progress: Optional[int] = Field(None, ge=0, le=100)
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskProgressUpdate(BaseModel):
    """更新任务进度"""
    progress: int = Field(..., ge=0, le=100)
    content: Optional[str] = Field(None, max_length=1000)  # 当日工作内容


class TaskResponse(TaskBase):
    """任务响应"""
    id: int
    creator_id: int
    assignee_id: Optional[int] = None
    status: str
    progress: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskWithUsers(TaskResponse):
    """带用户信息的任务"""
    creator_name: str
    assignee_name: Optional[str] = None


class TaskBrief(BaseModel):
    """任务简要信息（用于日报选择）"""
    id: int
    title: str
    project_name: Optional[str] = None
    status: str
    progress: int

    class Config:
        from_attributes = True


# ==================== TaskProgressLog Schemas ====================

class TaskProgressLogResponse(BaseModel):
    """任务进度日志响应"""
    id: int
    task_id: int
    daily_report_item_id: Optional[int] = None
    date: date
    progress_before: Optional[int] = None
    progress_after: Optional[int] = None
    content: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskWithLogs(TaskResponse):
    """带进度日志的任务详情"""
    progress_logs: list[TaskProgressLogResponse] = []
    creator_name: str
    assignee_name: Optional[str] = None


# ==================== 筛选参数 ====================

class TaskFilterParams(BaseModel):
    """任务筛选参数"""
    status: Optional[str] = None
    project_name: Optional[str] = None
    assignee_id: Optional[int] = None
    creator_id: Optional[int] = None
    include_completed: bool = False  # 是否包含已完成任务
