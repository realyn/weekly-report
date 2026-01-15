import request from './request'

export const projectsApi = {
  // ========== 项目查询 ==========

  // 获取所有项目（简要信息）
  getProjects() {
    return request.get('/admin/projects/')
  },

  // 获取所有项目（完整详情含子项目）
  getProjectsDetail() {
    return request.get('/admin/projects/detail')
  },

  // 获取单个项目详情
  getProject(name) {
    return request.get(`/admin/projects/detail/${encodeURIComponent(name)}`)
  },

  // ========== 项目 CRUD ==========

  // 创建项目
  createProject(data) {
    return request.post('/admin/projects/create', data)
  },

  // 更新项目
  updateProject(name, data) {
    return request.put(`/admin/projects/update/${encodeURIComponent(name)}`, data)
  },

  // 重命名项目
  renameProject(name, newName) {
    return request.put(`/admin/projects/rename/${encodeURIComponent(name)}`, { new_name: newName })
  },

  // 删除项目
  deleteProject(name) {
    return request.delete(`/admin/projects/delete/${encodeURIComponent(name)}`)
  },

  // ========== 子项目管理 ==========

  // 添加子项目
  addSubItem(projectName, name, description = '') {
    return request.post(`/admin/projects/${encodeURIComponent(projectName)}/sub-items`, { name, description })
  },

  // 更新子项目
  updateSubItem(projectName, subName, data) {
    return request.put(`/admin/projects/${encodeURIComponent(projectName)}/sub-items/${encodeURIComponent(subName)}`, data)
  },

  // 删除子项目
  removeSubItem(projectName, subName) {
    return request.delete(`/admin/projects/${encodeURIComponent(projectName)}/sub-items/${encodeURIComponent(subName)}`)
  },

  // ========== 类别管理 ==========

  // 获取项目类别
  getCategories() {
    return request.get('/admin/projects/categories')
  },

  // 添加类别
  addCategory(name) {
    return request.post('/admin/projects/categories', { name })
  },

  // 删除类别
  removeCategory(name) {
    return request.delete(`/admin/projects/categories/${encodeURIComponent(name)}`)
  },

  // ========== 待审核项目管理 ==========

  // 获取待审核项目
  getPending() {
    return request.get('/admin/projects/pending')
  },

  // 获取黑名单
  getRejected() {
    return request.get('/admin/projects/rejected')
  },

  // 确认待审核项目
  approve(name, category = '其他') {
    return request.post('/admin/projects/approve', { name, category })
  },

  // 合并到已有项目
  merge(pendingName, targetProject) {
    return request.post('/admin/projects/merge', {
      pending_name: pendingName,
      target_project: targetProject
    })
  },

  // 拒绝待审核项目
  reject(name) {
    return request.post('/admin/projects/reject', { name })
  },

  // 添加别名
  addAlias(projectName, alias) {
    return request.post('/admin/projects/alias', {
      project_name: projectName,
      alias
    })
  },

  // 从黑名单移除
  removeFromRejected(name) {
    return request.delete(`/admin/projects/rejected/${encodeURIComponent(name)}`)
  },

  // ========== Embedding 管理 ==========

  // 重建向量索引
  rebuildEmbeddings() {
    return request.post('/admin/projects/rebuild-embeddings')
  }
}
