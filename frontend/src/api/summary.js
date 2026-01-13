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

  getChartData(year) {
    return request.get('/summary/chart-data', { params: { year } })
  }
}
