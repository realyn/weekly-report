import request from './request'

export const dailyReportApi = {
  // 获取今日日报
  getCurrent() {
    return request.get('/daily-reports/current')
  },

  // 获取日报列表
  getList(startDate, endDate) {
    const params = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    return request.get('/daily-reports/', { params })
  },

  // 获取单个日报
  getById(id) {
    return request.get(`/daily-reports/${id}`)
  },

  // 创建日报
  create(data) {
    return request.post('/daily-reports/', data)
  },

  // 更新日报
  update(id, data) {
    return request.put(`/daily-reports/${id}`, data)
  },

  // 删除日报
  delete(id) {
    return request.delete(`/daily-reports/${id}`)
  },

  // 获取截止时间信息
  getDeadline(reportDate) {
    return request.get('/daily-reports/deadline', { params: { report_date: reportDate } })
  },

  // 解析预览（LLM 调用需要更长超时）
  parsePreview(workContent) {
    return request.post('/daily-reports/parse-preview', {
      work_content: workContent
    }, { timeout: 60000 })
  },

  // 获取本周日报汇总（用于生成周报）
  getWeekSummary(year, weekNum) {
    const params = {}
    if (year) params.year = year
    if (weekNum) params.week_num = weekNum
    return request.get('/daily-reports/week-summary', { params })
  },

  // 管理员获取所有用户日报
  adminGetList(startDate, endDate) {
    const params = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    return request.get('/daily-reports/admin/list', { params })
  },

  // 管理员更新工时
  adminUpdateItemHours(itemId, hours) {
    return request.put(`/daily-reports/admin/item/${itemId}/hours`, { hours })
  }
}
