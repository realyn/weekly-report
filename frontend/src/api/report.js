import request from './request'

export const reportApi = {
  getCurrent() {
    return request.get('/reports/current')
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
  }
}
