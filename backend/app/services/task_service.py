from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, datetime
from app.models.task import Task, TaskProgressLog
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskProgressUpdate


async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[Task]:
    """通过ID获取任务"""
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.progress_logs))
        .where(Task.id == task_id)
    )
    return result.scalar_one_or_none()


async def get_task_with_users(db: AsyncSession, task_id: int) -> Optional[tuple]:
    """获取任务及用户信息"""
    result = await db.execute(
        select(Task, User)
        .join(User, Task.creator_id == User.id)
        .options(selectinload(Task.progress_logs))
        .where(Task.id == task_id)
    )
    row = result.first()
    if not row:
        return None
    return row


async def get_tasks(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
    project_name: Optional[str] = None,
    include_completed: bool = False,
    only_assigned: bool = False
) -> List[Task]:
    """
    获取用户相关的任务列表
    - 用户创建的任务
    - 分配给用户的任务
    """
    query = select(Task).options(selectinload(Task.progress_logs))

    if only_assigned:
        # 只获取分配给该用户的任务
        query = query.where(Task.assignee_id == user_id)
    else:
        # 获取用户创建的或分配给用户的任务
        query = query.where(
            or_(Task.creator_id == user_id, Task.assignee_id == user_id)
        )

    if status:
        query = query.where(Task.status == status)
    elif not include_completed:
        # 默认不包含已完成和已取消的任务
        query = query.where(Task.status.in_(["pending", "in_progress"]))

    if project_name:
        query = query.where(Task.project_name == project_name)

    query = query.order_by(Task.priority.desc(), Task.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_my_active_tasks(db: AsyncSession, user_id: int) -> List[Task]:
    """获取用户进行中的任务（用于日报选择）"""
    result = await db.execute(
        select(Task)
        .where(
            and_(
                or_(Task.creator_id == user_id, Task.assignee_id == user_id),
                Task.status.in_(["pending", "in_progress"])
            )
        )
        .order_by(Task.priority.desc(), Task.updated_at.desc())
    )
    return list(result.scalars().all())


async def create_task(db: AsyncSession, user_id: int, task_data: TaskCreate) -> Task:
    """创建任务"""
    task = Task(
        title=task_data.title,
        description=task_data.description,
        project_name=task_data.project_name,
        creator_id=user_id,
        assignee_id=task_data.assignee_id or user_id,  # 默认分配给自己
        priority=task_data.priority,
        start_date=task_data.start_date,
        due_date=task_data.due_date,
        status="pending",
        progress=0
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task: Task, task_data: TaskUpdate) -> Task:
    """更新任务"""
    update_data = task_data.model_dump(exclude_unset=True)

    # 处理状态变更
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "completed" and task.status != "completed":
            task.completed_at = datetime.now()
        elif new_status != "completed":
            task.completed_at = None

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


async def update_task_progress(
    db: AsyncSession,
    task: Task,
    progress_data: TaskProgressUpdate,
    report_item_id: Optional[int] = None
) -> Task:
    """
    更新任务进度并记录日志
    """
    progress_before = task.progress
    progress_after = progress_data.progress

    # 记录进度日志
    log = TaskProgressLog(
        task_id=task.id,
        daily_report_item_id=report_item_id,
        date=date.today(),
        progress_before=progress_before,
        progress_after=progress_after,
        content=progress_data.content
    )
    db.add(log)

    # 更新任务进度
    task.progress = progress_after

    # 自动更新状态
    if progress_after == 100 and task.status != "completed":
        task.status = "completed"
        task.completed_at = datetime.now()
    elif progress_after > 0 and task.status == "pending":
        task.status = "in_progress"

    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task):
    """删除任务"""
    await db.delete(task)
    await db.commit()


async def get_task_progress_logs(db: AsyncSession, task_id: int) -> List[TaskProgressLog]:
    """获取任务进度日志"""
    result = await db.execute(
        select(TaskProgressLog)
        .where(TaskProgressLog.task_id == task_id)
        .order_by(TaskProgressLog.date.desc(), TaskProgressLog.created_at.desc())
    )
    return list(result.scalars().all())


async def can_manage_task(task: Task, user_id: int, is_admin: bool) -> bool:
    """检查用户是否有权限管理任务"""
    if is_admin:
        return True
    return task.creator_id == user_id


async def can_update_progress(task: Task, user_id: int, is_admin: bool) -> bool:
    """检查用户是否有权限更新任务进度"""
    if is_admin:
        return True
    return task.creator_id == user_id or task.assignee_id == user_id
