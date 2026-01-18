import request from './request'

export const taskApi = {
  // 获取任务列表
  getList(params = {}) {
    return request.get('/tasks/', { params })
  },

  // 获取我的进行中任务（用于日报选择）
  getMyTasks() {
    return request.get('/tasks/my-tasks')
  },

  // 获取单个任务详情
  getById(id) {
    return request.get(`/tasks/${id}`)
  },

  // 创建任务
  create(data) {
    return request.post('/tasks/', data)
  },

  // 更新任务
  update(id, data) {
    return request.put(`/tasks/${id}`, data)
  },

  // 更新任务进度
  updateProgress(id, data) {
    return request.put(`/tasks/${id}/progress`, data)
  },

  // 删除任务
  delete(id) {
    return request.delete(`/tasks/${id}`)
  }
}
