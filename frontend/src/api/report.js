import request from './request'

export const reportApi = {
  getCurrent() {
    return request.get('/reports/current')
  },

  getYears() {
    return request.get('/reports/years')
  },

  getProjects() {
    return request.get('/reports/projects')
  },

  getList(year, weekNum) {
    const params = {}
    if (year) params.year = year
    if (weekNum) params.week_num = weekNum
    return request.get('/reports/', { params })
  },

  getById(id) {
    return request.get(`/reports/${id}`)
  },

  create(data) {
    return request.post('/reports/', data)
  },

  update(id, data) {
    return request.put(`/reports/${id}`, data)
  },

  delete(id) {
    return request.delete(`/reports/${id}`)
  },

  getDeadline(year, week) {
    return request.get('/reports/deadline', { params: { year, week } })
  },

  // 解析预览（LLM 调用需要更长超时）
  parsePreview(thisWeekWork, nextWeekPlan) {
    return request.post('/reports/parse-preview', {
      this_week_work: thisWeekWork,
      next_week_plan: nextWeekPlan
    }, { timeout: 60000 })
  },

  // 管理员查看指定用户的周报
  getUserReports(userId, year) {
    const params = {}
    if (year) params.year = year
    return request.get(`/reports/admin/user/${userId}`, { params })
  },

  // 提交新项目建议
  suggestProject(projectName) {
    return request.post('/projects/suggest', { name: projectName })
  },

  // 提交新子分类建议
  suggestSubItem(projectName, subItemName) {
    return request.post('/projects/suggest-sub-item', {
      project_name: projectName,
      sub_item_name: subItemName
    })
  }
}
