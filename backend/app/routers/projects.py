from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.utils.security import get_current_admin
from app.models.user import User
from app.services.llm_service import get_project_extractor

router = APIRouter(prefix="/api/admin/projects", tags=["项目管理"])


# ========== 请求模型 ==========

class SubItem(BaseModel):
    name: str
    description: str = ""


class ProjectCreate(BaseModel):
    name: str
    category: str = "其他"
    description: str = ""
    aliases: List[str] = []
    sub_items: List[SubItem] = []


class ProjectUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    aliases: Optional[List[str]] = None
    sub_items: Optional[List[SubItem]] = None


class ProjectRename(BaseModel):
    new_name: str


class ProjectApproveRequest(BaseModel):
    name: str
    category: Optional[str] = "其他"


class ProjectMergeRequest(BaseModel):
    pending_name: str
    target_project: str


class ProjectRejectRequest(BaseModel):
    name: str


class AliasAddRequest(BaseModel):
    project_name: str
    alias: str


class SubItemAdd(BaseModel):
    name: str
    description: str = ""


class SubItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryRequest(BaseModel):
    name: str


# ========== 项目管理 API ==========

@router.get("/")
async def list_all_projects(admin: User = Depends(get_current_admin)):
    """获取所有项目（简要信息）"""
    extractor = get_project_extractor()
    projects = extractor.get_all_projects()
    return {"code": 200, "data": projects}


@router.get("/detail")
async def list_all_projects_detail(admin: User = Depends(get_current_admin)):
    """获取所有项目（完整详情含子项目）"""
    extractor = get_project_extractor()
    projects = extractor.get_all_projects_detail()
    return {"code": 200, "data": projects}


@router.get("/detail/{name}")
async def get_project_detail(name: str, admin: User = Depends(get_current_admin)):
    """获取单个项目详情"""
    extractor = get_project_extractor()
    project = extractor.get_project(name)
    if project:
        return {"code": 200, "data": project}
    raise HTTPException(status_code=404, detail="项目不存在")


@router.post("/create")
async def create_project(
    data: ProjectCreate,
    admin: User = Depends(get_current_admin)
):
    """创建新项目"""
    extractor = get_project_extractor()
    sub_items = [{"name": s.name, "description": s.description} for s in data.sub_items]
    success = extractor.create_project(
        name=data.name,
        category=data.category,
        description=data.description,
        aliases=data.aliases,
        sub_items=sub_items
    )
    if success:
        return {"code": 200, "message": f"项目「{data.name}」创建成功"}
    raise HTTPException(status_code=400, detail="项目已存在")


@router.put("/update/{name}")
async def update_project(
    name: str,
    data: ProjectUpdate,
    admin: User = Depends(get_current_admin)
):
    """更新项目信息"""
    extractor = get_project_extractor()
    updates = data.model_dump(exclude_unset=True)
    if "sub_items" in updates and updates["sub_items"] is not None:
        updates["sub_items"] = [{"name": s.name, "description": s.description} for s in data.sub_items]

    success = extractor.update_project(name, updates)
    if success:
        return {"code": 200, "message": "更新成功"}
    raise HTTPException(status_code=404, detail="项目不存在")


@router.put("/rename/{name}")
async def rename_project(
    name: str,
    data: ProjectRename,
    admin: User = Depends(get_current_admin)
):
    """重命名项目"""
    extractor = get_project_extractor()
    success = extractor.rename_project(name, data.new_name)
    if success:
        return {"code": 200, "message": f"已重命名为「{data.new_name}」"}
    raise HTTPException(status_code=400, detail="重命名失败（项目不存在或新名称已被使用）")


@router.delete("/delete/{name}")
async def delete_project(name: str, admin: User = Depends(get_current_admin)):
    """删除项目"""
    extractor = get_project_extractor()
    success = extractor.delete_project(name)
    if success:
        return {"code": 200, "message": f"项目「{name}」已删除"}
    raise HTTPException(status_code=404, detail="项目不存在")


# ========== 子项目管理 ==========

@router.post("/{project_name}/sub-items")
async def add_sub_item(
    project_name: str,
    data: SubItemAdd,
    admin: User = Depends(get_current_admin)
):
    """添加子项目"""
    extractor = get_project_extractor()
    success = extractor.add_sub_item(project_name, data.name, data.description)
    if success:
        return {"code": 200, "message": f"已添加子项目「{data.name}」"}
    raise HTTPException(status_code=400, detail="添加失败（项目不存在或子项目已存在）")


@router.put("/{project_name}/sub-items/{sub_name}")
async def update_sub_item(
    project_name: str,
    sub_name: str,
    data: SubItemUpdate,
    admin: User = Depends(get_current_admin)
):
    """更新子项目"""
    extractor = get_project_extractor()
    updates = data.model_dump(exclude_unset=True)
    success = extractor.update_sub_item(project_name, sub_name, updates)
    if success:
        return {"code": 200, "message": "更新成功"}
    raise HTTPException(status_code=404, detail="子项目不存在")


@router.delete("/{project_name}/sub-items/{sub_name}")
async def remove_sub_item(
    project_name: str,
    sub_name: str,
    admin: User = Depends(get_current_admin)
):
    """删除子项目"""
    extractor = get_project_extractor()
    success = extractor.remove_sub_item(project_name, sub_name)
    if success:
        return {"code": 200, "message": f"已删除子项目「{sub_name}」"}
    raise HTTPException(status_code=404, detail="子项目不存在")


# ========== 类别管理 ==========

@router.get("/categories")
async def list_categories(admin: User = Depends(get_current_admin)):
    """获取所有项目类别"""
    extractor = get_project_extractor()
    categories = extractor.get_categories()
    return {"code": 200, "data": categories}


@router.post("/categories")
async def add_category(data: CategoryRequest, admin: User = Depends(get_current_admin)):
    """添加项目类别"""
    extractor = get_project_extractor()
    success = extractor.add_category(data.name)
    if success:
        return {"code": 200, "message": f"已添加类别「{data.name}」"}
    raise HTTPException(status_code=400, detail="类别已存在")


@router.delete("/categories/{name}")
async def remove_category(name: str, admin: User = Depends(get_current_admin)):
    """删除项目类别"""
    extractor = get_project_extractor()
    success = extractor.remove_category(name)
    if success:
        return {"code": 200, "message": f"已删除类别「{name}」"}
    raise HTTPException(status_code=404, detail="类别不存在")


# ========== 待审核项目管理 ==========

@router.get("/pending")
async def list_pending_projects(admin: User = Depends(get_current_admin)):
    """获取待审核项目列表"""
    extractor = get_project_extractor()
    pending = extractor.get_pending_projects()
    return {"code": 200, "data": pending}


@router.get("/rejected")
async def list_rejected_projects(admin: User = Depends(get_current_admin)):
    """获取已拒绝（黑名单）项目列表"""
    extractor = get_project_extractor()
    rejected = extractor.get_rejected_list()
    return {"code": 200, "data": rejected}


@router.post("/approve")
async def approve_project(
    request: ProjectApproveRequest,
    admin: User = Depends(get_current_admin)
):
    """确认待审核项目，加入正式列表"""
    extractor = get_project_extractor()
    success = extractor.approve_pending_project(request.name, request.category)
    if success:
        return {"code": 200, "message": f"已将「{request.name}」添加到「{request.category}」类别"}
    raise HTTPException(status_code=400, detail="项目不在待审核列表中")


@router.post("/merge")
async def merge_project(
    request: ProjectMergeRequest,
    admin: User = Depends(get_current_admin)
):
    """将待审核项目合并到已有项目（作为别名）"""
    extractor = get_project_extractor()
    success = extractor.merge_pending_to_existing(request.pending_name, request.target_project)
    if success:
        return {"code": 200, "message": f"已将「{request.pending_name}」作为「{request.target_project}」的别名"}
    raise HTTPException(status_code=400, detail="操作失败：待审核项目不存在或目标项目不存在")


@router.post("/reject")
async def reject_project(
    request: ProjectRejectRequest,
    admin: User = Depends(get_current_admin)
):
    """拒绝待审核项目（加入黑名单）"""
    extractor = get_project_extractor()
    success = extractor.reject_pending_project(request.name)
    if success:
        return {"code": 200, "message": f"已将「{request.name}」加入黑名单"}
    raise HTTPException(status_code=400, detail="项目不在待审核列表中")


@router.post("/alias")
async def add_alias(
    request: AliasAddRequest,
    admin: User = Depends(get_current_admin)
):
    """为已有项目添加别名"""
    extractor = get_project_extractor()
    success = extractor.add_alias(request.project_name, request.alias)
    if success:
        return {"code": 200, "message": f"已为「{request.project_name}」添加别名「{request.alias}」"}
    raise HTTPException(status_code=400, detail="项目不存在")


@router.delete("/rejected/{name}")
async def remove_from_rejected(
    name: str,
    admin: User = Depends(get_current_admin)
):
    """从黑名单中移除"""
    extractor = get_project_extractor()
    success = extractor.remove_from_rejected(name)
    if success:
        return {"code": 200, "message": f"已将「{name}」从黑名单移除"}
    raise HTTPException(status_code=400, detail="项目不在黑名单中")


# ========== Embedding 管理 ==========

@router.post("/rebuild-embeddings")
async def rebuild_embeddings(admin: User = Depends(get_current_admin)):
    """重建项目向量索引（管理员）"""
    extractor = get_project_extractor()
    try:
        await extractor.rebuild_embeddings()
        return {"code": 200, "message": "向量索引重建完成"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建失败: {str(e)}")
