import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dailyReportApi } from '../api/dailyReport'

export const useDailyReportStore = defineStore('dailyReport', () => {
  const currentReport = ref(null)
  const reports = ref([])
  const loading = ref(false)
  const weekSummary = ref(null)

  // 获取今日日报
  const fetchCurrentReport = async () => {
    loading.value = true
    try {
      currentReport.value = await dailyReportApi.getCurrent()
    } finally {
      loading.value = false
    }
  }

  // 获取日报列表
  const fetchReports = async (startDate, endDate) => {
    loading.value = true
    try {
      reports.value = await dailyReportApi.getList(startDate, endDate)
    } finally {
      loading.value = false
    }
  }

  // 获取特定日期的日报
  const fetchReportByDate = async (date) => {
    loading.value = true
    try {
      const list = await dailyReportApi.getList(date, date)
      currentReport.value = list.length > 0 ? list[0] : null
    } finally {
      loading.value = false
    }
  }

  // 保存日报（自动判断创建或更新）
  const saveReport = async (reportData) => {
    if (currentReport.value?.id) {
      currentReport.value = await dailyReportApi.update(currentReport.value.id, reportData)
    } else {
      currentReport.value = await dailyReportApi.create(reportData)
    }
    return currentReport.value
  }

  // 删除日报
  const deleteReport = async (id) => {
    await dailyReportApi.delete(id)
    if (currentReport.value?.id === id) {
      currentReport.value = null
    }
    reports.value = reports.value.filter(r => r.id !== id)
  }

  // 获取本周日报汇总
  const fetchWeekSummary = async (year, weekNum) => {
    loading.value = true
    try {
      weekSummary.value = await dailyReportApi.getWeekSummary(year, weekNum)
    } finally {
      loading.value = false
    }
  }

  // 重置当前日报
  const resetCurrentReport = () => {
    currentReport.value = null
  }

  return {
    currentReport,
    reports,
    loading,
    weekSummary,
    fetchCurrentReport,
    fetchReports,
    fetchReportByDate,
    saveReport,
    deleteReport,
    fetchWeekSummary,
    resetCurrentReport
  }
})
