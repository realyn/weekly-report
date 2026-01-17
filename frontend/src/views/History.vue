<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { reportApi } from '../api/report'
import { useUserStore } from '../stores/user'
import request from '../api/request'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.user?.role === 'admin')

const currentYear = new Date().getFullYear()
const year = ref(currentYear)
const yearOptions = ref([currentYear]) // 默认当前年份
const reports = ref([])
const loading = ref(false)

// 管理员功能：用户列表和选中用户
const users = ref([])
const selectedUserId = ref(null)
const loadingUsers = ref(false)

// ISO 周计算函数（与Chart.vue保持一致）
const getMondayOfWeek = (isoYear, isoWeek) => {
  const jan4 = new Date(isoYear, 0, 4)
  const jan4Day = jan4.getDay() || 7
  const firstMonday = new Date(isoYear, 0, 4 - (jan4Day - 1))
  const targetMonday = new Date(firstMonday)
  targetMonday.setDate(firstMonday.getDate() + (isoWeek - 1) * 7)
  return targetMonday
}

// 获取周在月份中的信息
const getWeekMonthInfo = (isoYear, isoWeek) => {
  const monday = getMondayOfWeek(isoYear, isoWeek)
  const month = monday.getMonth() + 1
  const monthYear = monday.getFullYear()

  // 找到该月第一个周一
  const firstDayOfMonth = new Date(monthYear, month - 1, 1)
  let firstMonday = new Date(firstDayOfMonth)
  const dayOfWeek = firstDayOfMonth.getDay()
  if (dayOfWeek !== 1) {
    const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek)
    firstMonday.setDate(firstDayOfMonth.getDate() + daysUntilMonday)
  }

  // 计算当前周是该月第几周
  const weekDiff = Math.round((monday - firstMonday) / (7 * 24 * 60 * 60 * 1000))
  const weekInMonth = weekDiff + 1

  return { month, weekInMonth, monthYear }
}

// 格式化周显示（简短版，不含月份）
const formatWeekLabel = (report) => {
  const { weekInMonth } = getWeekMonthInfo(report.year, report.week_num)
  return `第${weekInMonth}周`
}

// 获取周的日期范围
const getWeekDateRange = (report) => {
  const monday = getMondayOfWeek(report.year, report.week_num)
  const sunday = new Date(monday)
  sunday.setDate(sunday.getDate() + 6)
  const formatDate = (d) => `${d.getMonth() + 1}.${d.getDate()}`
  return `${formatDate(monday)} - ${formatDate(sunday)}`
}

// 获取报告所属月份的key
const getMonthKey = (report) => {
  const { month, monthYear } = getWeekMonthInfo(report.year, report.week_num)
  return `${monthYear}-${month}`
}

// 获取月份显示文本
const getMonthLabel = (report) => {
  const { month, monthYear } = getWeekMonthInfo(report.year, report.week_num)
  if (monthYear !== report.year) {
    return `${monthYear}年${month}月`
  }
  return `${month}月`
}

// 按月份分组的报告
const groupedReports = computed(() => {
  const groups = []
  let currentMonth = null

  for (const report of reports.value) {
    const monthKey = getMonthKey(report)
    if (monthKey !== currentMonth) {
      currentMonth = monthKey
      groups.push({
        monthKey,
        monthLabel: getMonthLabel(report),
        reports: []
      })
    }
    groups[groups.length - 1].reports.push(report)
  }

  return groups
})

// 获取用户列表（管理员）
const fetchUsers = async () => {
  if (!isAdmin.value) return
  loadingUsers.value = true
  try {
    const data = await request.get('/admin/users/')
    // 过滤出活跃用户，管理员排第一
    users.value = data
      .filter(u => u.is_active)
      .sort((a, b) => {
        if (a.role === 'admin' && b.role !== 'admin') return -1
        if (a.role !== 'admin' && b.role === 'admin') return 1
        return a.id - b.id
      })
    // 默认选中当前用户
    if (userStore.user) {
      selectedUserId.value = userStore.user.id
    }
  } finally {
    loadingUsers.value = false
  }
}

const fetchYears = async () => {
  try {
    const years = await reportApi.getYears()
    // 确保当前年份在列表中，即使没有数据
    if (!years.includes(currentYear)) {
      years.unshift(currentYear)
    }
    yearOptions.value = years.sort((a, b) => a - b) // 升序排列
    // 默认选中最新年份
    if (years.length > 0) {
      year.value = years[years.length - 1]
    }
  } catch (e) {
    yearOptions.value = [currentYear]
  }
}

const fetchReports = async () => {
  loading.value = true
  try {
    if (isAdmin.value && selectedUserId.value && selectedUserId.value !== userStore.user?.id) {
      // 管理员查看其他用户的周报
      reports.value = await reportApi.getUserReports(selectedUserId.value, year.value)
    } else {
      // 查看自己的周报
      reports.value = await reportApi.getList(year.value)
    }
  } catch (e) {
    // error handled
  } finally {
    loading.value = false
  }
}

// 切换用户时重新加载
watch(selectedUserId, () => {
  fetchReports()
})

onMounted(async () => {
  await fetchUsers()
  await fetchYears()
  fetchReports()
})

</script>

<template>
  <div class="page-container">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">历史周报</h1>
        <div class="year-tabs">
          <button
            v-for="y in yearOptions"
            :key="y"
            class="year-tab"
            :class="{ active: year === y }"
            @click="year = y; fetchReports()"
          >
            {{ y }}
          </button>
        </div>
      </div>

      <!-- 管理员用户切换标签 -->
      <div v-if="isAdmin && users.length > 0" class="user-tabs-container">
        <div class="user-tabs">
          <button
            v-for="user in users"
            :key="user.id"
            class="user-tab"
            :class="{ active: selectedUserId === user.id }"
            @click="selectedUserId = user.id"
          >
            {{ user.real_name }}
          </button>
        </div>
      </div>

      <!-- 历史记录列表 -->
      <div class="card">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div class="table-container" v-else-if="reports.length">
          <table class="member-table">
            <thead>
              <tr>
                <th style="width: 140px">周期</th>
                <th>本周工作</th>
                <th>下周计划</th>
                <th style="width: 160px">更新时间</th>
              </tr>
            </thead>
            <template v-for="group in groupedReports" :key="group.monthKey">
              <tbody>
                <tr class="month-separator">
                  <td colspan="4">
                    <div class="month-label">{{ group.monthLabel }}</div>
                  </td>
                </tr>
                <tr v-for="report in group.reports" :key="report.id">
                  <td>
                    <div class="week-info-cell">
                      <span class="week-label">{{ formatWeekLabel(report) }}</span>
                      <span class="week-date">{{ getWeekDateRange(report) }}</span>
                    </div>
                  </td>
                  <td class="work-cell">
                    <div class="work-content">{{ report.this_week_work }}</div>
                  </td>
                  <td class="work-cell">
                    <div class="work-content">{{ report.next_week_plan }}</div>
                  </td>
                  <td class="time-cell">
                    {{ new Date(report.updated_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}
                  </td>
                </tr>
              </tbody>
            </template>
          </table>
        </div>

        <div class="empty-state" v-else>
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-6l-2 3h-4l-2-3H2"/>
            <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>
          </svg>
          <p>暂无历史周报</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* v0.app 风格 */
.page-container {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #f8fafc;
}

.page-content {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
  letter-spacing: -0.025em;
}

/* 年份切换按钮 */
.year-tabs {
  display: flex;
  gap: 8px;
}

.year-tab {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #64748b;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.year-tab:hover {
  border-color: #7aaed8;
  color: #7aaed8;
  background: #f0f7fc;
}

.year-tab.active {
  background: #7aaed8;
  color: white;
  border-color: #7aaed8;
}

/* 用户切换标签 */
.user-tabs-container {
  margin-bottom: 16px;
  background: white;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.user-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.user-tab {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: white;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.user-tab:hover {
  border-color: #7aaed8;
  color: #7aaed8;
  background: #f0f7fc;
}

.user-tab.active {
  background: #7aaed8;
  color: white;
  border-color: #7aaed8;
}

/* 卡片 */
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

/* 表格 */
.table-container {
  overflow-x: auto;
  border-radius: 8px;
}

.member-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.member-table th,
.member-table td {
  padding: 14px 16px;
  text-align: left;
}

.member-table th {
  background: transparent;
  color: #64748b;
  font-weight: 500;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.member-table td {
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
  color: #334155;
}

.member-table tbody tr:hover {
  background: #f8fafc;
}

.week-info-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.week-label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.week-date {
  font-size: 12px;
  color: #94a3b8;
}

.work-cell {
  max-width: 280px;
}

.work-content {
  white-space: pre-line;
  line-height: 1.6;
  font-size: 14px;
  color: #475569;
}

/* 月份分隔行 */
.month-separator td {
  background: #f8fafc;
  padding: 10px 16px !important;
  border-bottom: 1px solid #f1f5f9;
}

.month-label {
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
}

.time-cell {
  font-size: 13px;
  color: #64748b;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #64748b;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e2e8f0;
  border-top-color: #7aaed8;
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
  color: #64748b;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #94a3b8;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 16px;
    flex-direction: column;
    gap: 12px;
  }

  .page-title {
    font-size: 1.25rem;
  }

  .user-tabs-container {
    padding: 12px 16px;
  }

  .user-tabs {
    gap: 6px;
  }

  .user-tab {
    padding: 6px 12px;
    font-size: 12px;
  }

  .work-cell {
    max-width: 150px;
  }
}
</style>
