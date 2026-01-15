import request from './request'

export const summaryApi = {
  getWeekly(year, week) {
    return request.get('/summary/weekly', { params: { year, week } })
  },

  downloadWord(year, week) {
    return request.get(`/summary/download/${year}/${week}`, {
      responseType: 'blob'
    })
  },

  getChartData(year, startWeek, endWeek) {
    return request.get('/summary/chart-data', {
      params: { year, start_week: startWeek, end_week: endWeek }
    })
  },

  getDashboard(year, week) {
    return request.get('/summary/dashboard', { params: { year, week } })
  },

  getLatestWeek() {
    return request.get('/summary/latest-week')
  },

  getAvailableWeeks() {
    return request.get('/summary/available-weeks')
  },

  triggerAnalysis(year, week) {
    return request.post('/summary/trigger-analysis', null, {
      params: { year, week }
    })
  }
}
