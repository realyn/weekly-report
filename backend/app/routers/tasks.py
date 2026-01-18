from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.database import get_db
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskWithUsers, TaskWithLogs,
    TaskBrief, TaskProgressUpdate
)
from app.services import task_service
from app.utils.security import get_current_user
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/tasks", tags=["任务"])
logger = logging.getLogger(__name__)


def build_task_response(task) -> TaskResponse:
    """构建任务响应"""
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        project_name=task.project_name,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        progress=task.progress,
        start_date=task.start_date,
        due_date=task.due_date,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.get("/my-tasks", response_model=list[TaskBrief])
async def get_my_active_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的进行中任务（用于日报选择）"""
    tasks = await task_service.get_my_active_tasks(db, current_user.id)
    return [
        TaskBrief(
            id=t.id,
            title=t.title,
            project_name=t.project_name,
            status=t.status,
            progress=t.progress
        )
        for t in tasks
    ]


@router.get("/", response_model=list[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    project_name: Optional[str] = None,
    include_completed: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取任务列表"""
    tasks = await task_service.get_tasks(
        db,
        user_id=current_user.id,
        status=status,
        project_name=project_name,
        include_completed=include_completed
    )
    return [build_task_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskWithLogs)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取任务详情"""
    row = await task_service.get_task_with_users(db, task_id)
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")

    task, creator = row

    # 检查权限：本人相关或管理员
    is_admin = current_user.role == UserRole.admin
    if not is_admin and task.creator_id != current_user.id and task.assignee_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该任务")

    # 获取负责人名称
    assignee_name = None
    if task.assignee_id:
        if task.assignee_id == task.creator_id:
            assignee_name = creator.real_name
        else:
            # 需要额外查询
            from sqlalchemy import select
            from app.models.user import User
            result = await db.execute(select(User).where(User.id == task.assignee_id))
            assignee = result.scalar_one_or_none()
            assignee_name = assignee.real_name if assignee else None

    return TaskWithLogs(
        id=task.id,
        title=task.title,
        description=task.description,
        project_name=task.project_name,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        status=task.status,
        priority=task.priority,
        progress=task.progress,
        start_date=task.start_date,
        due_date=task.due_date,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        progress_logs=task.progress_logs,
        creator_name=creator.real_name,
        assignee_name=assignee_name
    )


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建任务"""
    # 如果指定了负责人，检查权限（只有管理员可以分配给他人）
    if task_data.assignee_id and task_data.assignee_id != current_user.id:
        if current_user.role != UserRole.admin:
            raise HTTPException(status_code=403, detail="只有管理员可以将任务分配给他人")

    task = await task_service.create_task(db, current_user.id, task_data)
    return build_task_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新任务"""
    task = await task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查权限
    is_admin = current_user.role == UserRole.admin
    if not await task_service.can_manage_task(task, current_user.id, is_admin):
        raise HTTPException(status_code=403, detail="无权修改该任务")

    # 如果要分配给他人，检查权限
    if task_data.assignee_id and task_data.assignee_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以将任务分配给他人")

    task = await task_service.update_task(db, task, task_data)
    return build_task_response(task)


@router.put("/{task_id}/progress", response_model=TaskResponse)
async def update_task_progress(
    task_id: int,
    progress_data: TaskProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新任务进度"""
    task = await task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查权限
    is_admin = current_user.role == UserRole.admin
    if not await task_service.can_update_progress(task, current_user.id, is_admin):
        raise HTTPException(status_code=403, detail="无权更新该任务进度")

    task = await task_service.update_task_progress(db, task, progress_data)
    return build_task_response(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除任务"""
    task = await task_service.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查权限
    is_admin = current_user.role == UserRole.admin
    if not await task_service.can_manage_task(task, current_user.id, is_admin):
        raise HTTPException(status_code=403, detail="无权删除该任务")

    await task_service.delete_task(db, task)
    return {"message": "任务已删除"}
