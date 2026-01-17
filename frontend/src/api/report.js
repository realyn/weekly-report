import request from './request'

export const reportApi = {
  getCurrent() {
    return request.get('/reports/current')
  },

  getYears() {
    return request.get('/reports/years')
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

  // 解析预览
  parsePreview(thisWeekWork, nextWeekPlan) {
    return request.post('/reports/parse-preview', {
      this_week_work: thisWeekWork,
      next_week_plan: nextWeekPlan
    })
  },

  // 管理员查看指定用户的周报
  getUserReports(userId, year) {
    const params = {}
    if (year) params.year = year
    return request.get(`/reports/admin/user/${userId}`, { params })
  }
}
