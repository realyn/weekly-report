import { defineStore } from 'pinia'
import { ref } from 'vue'
import { reportApi } from '../api/report'

export const useReportStore = defineStore('report', () => {
  const currentReport = ref(null)
  const reports = ref([])
  const loading = ref(false)

  const fetchCurrentReport = async () => {
    loading.value = true
    try {
      currentReport.value = await reportApi.getCurrent()
    } finally {
      loading.value = false
    }
  }

  const fetchReports = async (year, weekNum) => {
    loading.value = true
    try {
      reports.value = await reportApi.getList(year, weekNum)
    } finally {
      loading.value = false
    }
  }

  const saveReport = async (reportData) => {
    if (currentReport.value?.id) {
      currentReport.value = await reportApi.update(currentReport.value.id, reportData)
    } else {
      currentReport.value = await reportApi.create(reportData)
    }
    return currentReport.value
  }

  return {
    currentReport,
    reports,
    loading,
    fetchCurrentReport,
    fetchReports,
    saveReport
  }
})
