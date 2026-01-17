"""
项目建议路由 - 普通用户可访问
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.utils.security import get_current_user
from app.models.user import User
from app.services.llm_service import get_project_extractor
import logging

router = APIRouter(prefix="/api/projects", tags=["项目建议"])
logger = logging.getLogger(__name__)


class ProjectSuggestRequest(BaseModel):
    """项目建议请求"""
    name: str = Field(..., min_length=1, max_length=50, description="项目名称")


class SubItemSuggestRequest(BaseModel):
    """子分类建议请求"""
    project_name: str = Field(..., min_length=1, max_length=50, description="父项目名称")
    sub_item_name: str = Field(..., min_length=1, max_length=50, description="子分类名称")


@router.post("/suggest")
async def suggest_project(
    request: ProjectSuggestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    用户建议新项目

    建议的项目会进入待审核列表，等待管理员审批。
    """
    extractor = get_project_extractor()
    project_name = request.name.strip()

    if not project_name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    # 检查是否已存在于正式项目列表
    existing = extractor.get_project(project_name)
    if existing:
        raise HTTPException(status_code=400, detail=f"项目「{project_name}」已存在")

    # 检查是否已在待审核列表
    pending = extractor.get_pending_projects()
    if any(p.get("name", "").lower() == project_name.lower() for p in pending):
        raise HTTPException(status_code=400, detail=f"项目「{project_name}」已在审核中")

    # 检查是否在黑名单中
    rejected = extractor.get_rejected_list()
    if project_name.lower() in [r.lower() for r in rejected]:
        raise HTTPException(status_code=400, detail=f"项目「{project_name}」不可添加")

    # 添加到待审核列表
    success = extractor.add_pending_project(project_name, suggested_by=current_user.name)
    if not success:
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")

    logger.info(f"用户 {current_user.name} 建议新项目: {project_name}")

    return {
        "code": 200,
        "message": f"项目「{project_name}」已提交，等待管理员审核"
    }


@router.post("/suggest-sub-item")
async def suggest_sub_item(
    request: SubItemSuggestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    用户建议新子分类

    建议的子分类会进入待审核列表，等待管理员审批。
    """
    extractor = get_project_extractor()
    project_name = request.project_name.strip()
    sub_item_name = request.sub_item_name.strip()

    if not project_name:
        raise HTTPException(status_code=400, detail="父项目名称不能为空")

    if not sub_item_name:
        raise HTTPException(status_code=400, detail="子分类名称不能为空")

    # 检查父项目是否存在
    parent_project = extractor.get_project(project_name)
    if not parent_project:
        raise HTTPException(status_code=400, detail=f"父项目「{project_name}」不存在")

    # 检查子分类是否已存在于父项目中
    existing_sub_items = parent_project.get("sub_items", [])
    if any(s.get("name", "").lower() == sub_item_name.lower() for s in existing_sub_items):
        raise HTTPException(status_code=400, detail=f"子分类「{sub_item_name}」已存在于「{project_name}」中")

    # 检查是否已在待审核列表
    pending = extractor.get_pending_projects()
    for p in pending:
        if (p.get("type") == "sub_item" and
            p.get("parent_project", "").lower() == project_name.lower() and
            p.get("name", "").lower() == sub_item_name.lower()):
            raise HTTPException(status_code=400, detail=f"子分类「{sub_item_name}」已在审核中")

    # 添加到待审核列表
    success = extractor.add_pending_sub_item(project_name, sub_item_name, suggested_by=current_user.name)
    if not success:
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")

    logger.info(f"用户 {current_user.name} 建议新子分类: {project_name}/{sub_item_name}")

    return {
        "code": 200,
        "message": f"子分类「{sub_item_name}」已提交，等待管理员审核"
    }
