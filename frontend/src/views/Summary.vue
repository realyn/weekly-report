<script setup>
import { ref, onMounted, watch } from 'vue'
import { summaryApi } from '../api/summary'
import { ElMessage } from 'element-plus'

const currentYear = new Date().getFullYear()
const currentWeek = Math.ceil((new Date() - new Date(currentYear, 0, 1)) / (7 * 24 * 60 * 60 * 1000))

const year = ref(currentYear)
const week = ref(currentWeek)
const summaryData = ref(null)
const loading = ref(false)

const fetchSummary = async () => {
  loading.value = true
  try {
    const res = await summaryApi.getWeekly(year.value, week.value)
    summaryData.value = res.data
  } catch (e) {
    // error handled
  } finally {
    loading.value = false
  }
}

onMounted(fetchSummary)
watch([year, week], fetchSummary)

const downloadWord = async () => {
  try {
    const response = await summaryApi.downloadWord(year.value, week.value)
    const blob = new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `周报_${year.value}年第${week.value}周.docx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (e) {
    // error handled
  }
}
</script>

<template>
  <div class="summary-page">
    <el-card>
      <template #header>
        <div class="header">
          <div class="filters">
            <el-input-number v-model="year" :min="2020" :max="2030" />
            <span>年 第</span>
            <el-input-number v-model="week" :min="1" :max="53" />
            <span>周</span>
          </div>
          <el-button type="primary" @click="downloadWord" :disabled="!summaryData?.reports?.length">
            <el-icon><Download /></el-icon>
            下载Word
          </el-button>
        </div>
      </template>

      <div v-loading="loading">
        <div v-if="summaryData" class="summary-content">
          <div class="stats-row">
            <el-statistic title="团队成员" :value="summaryData.total_members" />
            <el-statistic title="已提交" :value="summaryData.submitted_count" />
            <el-statistic title="提交率" :value="summaryData.submission_rate" suffix="%" />
            <el-statistic title="任务总数" :value="summaryData.statistics?.total_tasks || 0" />
          </div>

          <el-divider />

          <h3>团队周报详情</h3>
          <el-table :data="summaryData.reports" stripe>
            <el-table-column prop="user_name" label="姓名" width="100" />
            <el-table-column prop="this_week_work" label="本周工作" show-overflow-tooltip />
            <el-table-column prop="next_week_plan" label="下周计划" show-overflow-tooltip />
            <el-table-column prop="task_count" label="任务数" width="80" />
          </el-table>
        </div>

        <el-empty v-else description="暂无数据" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.summary-page {
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stats-row {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
}
</style>
