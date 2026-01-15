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
  <div class="page-container">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">
          <svg class="title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 20V10M12 20V4M6 20v-6"/>
          </svg>
          周报汇总
        </h1>
        <div class="week-selector">
          <div class="selector-group">
            <input type="number" v-model.number="year" min="2020" max="2030" class="selector-input" />
            <span class="selector-label">年</span>
          </div>
          <div class="selector-group">
            <span class="selector-prefix">第</span>
            <input type="number" v-model.number="week" min="1" max="53" class="selector-input" />
            <span class="selector-label">周</span>
          </div>
        </div>
        <p class="page-subtitle" v-if="summaryData">{{ summaryData.date_range }}</p>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>

      <template v-else-if="summaryData">
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-number">{{ summaryData.total_members }}</div>
            <div class="stat-label">团队成员</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">{{ summaryData.submitted_count }}</div>
            <div class="stat-label">已提交</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">{{ summaryData.submission_rate }}%</div>
            <div class="stat-label">提交率</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">{{ summaryData.statistics?.total_tasks || 0 }}</div>
            <div class="stat-label">任务总数</div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-bar">
          <button class="btn btn-primary" @click="downloadWord" :disabled="!summaryData?.reports?.length">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
            </svg>
            下载Word文档
          </button>
        </div>

        <!-- 团队成员详情 -->
        <div class="card full-width">
          <div class="card-title">
            <svg class="title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
            </svg>
            团队成员周报详情
          </div>

          <div class="table-container" v-if="summaryData.reports?.length">
            <table class="member-table">
              <thead>
                <tr>
                  <th style="width: 100px">成员</th>
                  <th>本周工作</th>
                  <th>下周计划</th>
                  <th style="width: 80px">任务数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="report in summaryData.reports" :key="report.user_id">
                  <td><strong>{{ report.user_name }}</strong></td>
                  <td class="work-cell">
                    <div class="work-content">{{ report.this_week_work }}</div>
                  </td>
                  <td class="work-cell">
                    <div class="work-content">{{ report.next_week_plan }}</div>
                  </td>
                  <td class="task-cell">
                    <span class="task-count">{{ report.task_count }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="empty-state" v-else>
            <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 12h-6l-2 3h-4l-2-3H2"/>
              <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>
            </svg>
            <p>该周暂无已提交的周报</p>
          </div>
        </div>
      </template>

      <div class="empty-state" v-else>
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 12h-6l-2 3h-4l-2-3H2"/>
          <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>
        </svg>
        <p>暂无数据</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  min-height: calc(100vh - 64px);
  padding: 30px 20px;
}

.page-content {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
  color: white;
}

.page-title {
  font-size: 2.5em;
  font-weight: 700;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.title-icon {
  width: 1em;
  height: 1em;
  flex-shrink: 0;
}

.week-selector {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 12px;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-prefix {
  font-size: 1em;
  opacity: 0.9;
}

.selector-input {
  width: 80px;
  padding: 10px 14px;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  background: rgba(255, 255, 255, 0.95);
  color: #667eea;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.selector-input:focus {
  outline: none;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.selector-label {
  font-size: 1em;
  opacity: 0.9;
}

.page-subtitle {
  font-size: 1.2em;
  opacity: 0.9;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 25px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.stat-number {
  font-size: 2.5em;
  font-weight: bold;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  color: #666;
  font-size: 0.95em;
  margin-top: 5px;
}

/* 操作按钮 */
.action-bar {
  display: flex;
  justify-content: center;
  margin-bottom: 25px;
}

.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 卡片 */
.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 1.3em;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 3px solid #667eea;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

/* 表格 */
.table-container {
  overflow-x: auto;
}

.member-table {
  width: 100%;
  border-collapse: collapse;
}

.member-table th,
.member-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.member-table th {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 500;
  white-space: nowrap;
}

.member-table th:first-child {
  border-radius: 8px 0 0 0;
}

.member-table th:last-child {
  border-radius: 0 8px 0 0;
}

.member-table tr:hover {
  background: #f8f9ff;
}

.work-cell {
  max-width: 300px;
}

.work-content {
  white-space: pre-line;
  line-height: 1.6;
  font-size: 14px;
  color: #555;
  max-height: 120px;
  overflow-y: auto;
}

.task-cell {
  text-align: center;
}

.task-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 50%;
  font-size: 14px;
  font-weight: bold;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: white;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px;
  color: #999;
}

.card .empty-state {
  padding: 40px;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #94a3b8;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .week-selector {
    flex-direction: column;
    gap: 12px;
  }

  .work-cell {
    max-width: 200px;
  }
}
</style>
