<script setup>
import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { summaryApi } from '../api/summary'
import { ElMessage } from 'element-plus'

const currentYear = new Date().getFullYear()

// 年月周选择
const year = ref(currentYear)
const month = ref(1)
const weekOfMonth = ref(1)  // 当月第几周 (1-5)

// 可选年份范围
const availableYears = [2025, 2026]

// 获取日期的ISO周数和年份（使用本地时间，避免UTC时区偏移）
const getISOWeekAndYear = (date) => {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  d.setDate(d.getDate() + 4 - (d.getDay() || 7))
  const isoYear = d.getFullYear()
  const yearStart = new Date(isoYear, 0, 1)
  const isoWeek = Math.ceil((((d - yearStart) / 86400000) + 1) / 7)
  return { isoYear, isoWeek }
}

// 根据ISO年和周获取该周的周一日期
const getMondayOfWeek = (isoYear, isoWeek) => {
  // 使用 Jan 4 找到第一周（Jan 4 总是在ISO第1周内）
  const jan4 = new Date(isoYear, 0, 4)
  const jan4Day = jan4.getDay() || 7
  // 第1周的周一 = Jan 4 减去 (Jan 4的星期几 - 1)
  const firstMonday = new Date(isoYear, 0, 4 - (jan4Day - 1))
  // 目标周的周一
  const targetMonday = new Date(firstMonday)
  targetMonday.setDate(firstMonday.getDate() + (isoWeek - 1) * 7)
  return targetMonday
}

// 获取某月拥有的ISO周列表（周一在该月内的周才属于该月）
// 返回 [{isoYear, isoWeek}, ...] 格式，处理跨年情况
const getWeeksOwnedByMonth = (y, m) => {
  const weeks = []

  // 找到该月所有的周一
  const firstDay = new Date(y, m - 1, 1)
  const lastDay = new Date(y, m, 0) // 该月最后一天

  // 找到该月第一个周一
  let monday = new Date(firstDay)
  const dayOfWeek = monday.getDay()
  if (dayOfWeek !== 1) {
    // 如果不是周一，找到该月第一个周一
    const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek)
    monday.setDate(monday.getDate() + daysUntilMonday)
  }

  // 遍历该月所有周一
  while (monday <= lastDay) {
    const { isoYear, isoWeek } = getISOWeekAndYear(monday)
    weeks.push({ isoYear, isoWeek })
    monday.setDate(monday.getDate() + 7)
  }

  return weeks
}

// 当前月份可选的周（显示为第1周、第2周...）
const availableWeeksOfMonth = computed(() => {
  const weeks = getWeeksOwnedByMonth(year.value, month.value)
  return Array.from({ length: weeks.length }, (_, i) => i + 1)
})

// 将"当月第几周"转换为实际的ISO年和周数
const getActualWeekInfo = (y, m, weekOfM) => {
  const weeks = getWeeksOwnedByMonth(y, m)
  return weeks[weekOfM - 1] || weeks[0] || { isoYear: y, isoWeek: 1 }
}

// 计算实际周数用于API调用（返回ISO周数）
const week = computed(() => getActualWeekInfo(year.value, month.value, weekOfMonth.value).isoWeek)

// 计算实际年份用于API调用（可能跨年）
const actualYear = computed(() => getActualWeekInfo(year.value, month.value, weekOfMonth.value).isoYear)

// 根据ISO周数计算在该月是第几周
const getWeekOfMonthFromISO = (y, m, isoYear, isoWeek) => {
  const weeks = getWeeksOwnedByMonth(y, m)
  const index = weeks.findIndex(w => w.isoYear === isoYear && w.isoWeek === isoWeek)
  return index >= 0 ? index + 1 : 1
}

// 根据ISO年和周数找到它所属的显示月份（周一所在的月份）
const getMonthOfISOWeek = (isoYear, isoWeek) => {
  const monday = getMondayOfWeek(isoYear, isoWeek)
  return { year: monday.getFullYear(), month: monday.getMonth() + 1 }
}

// 获取所有有数据的周
const fetchAvailableWeeks = async () => {
  try {
    const res = await summaryApi.getAvailableWeeks()
    if (res.data) {
      availableWeeksData.value = res.data
    }
  } catch (e) {
    console.error('获取可用周失败', e)
  }
}

// 检查某年是否有数据（检查该年所有月份是否有数据）
const yearHasData = (y) => {
  // 检查该年每个月是否有数据
  for (let m = 1; m <= 12; m++) {
    if (monthHasData(y, m)) return true
  }
  return false
}

// 检查某月是否有数据
const monthHasData = (y, m) => {
  const monthWeeks = getWeeksOwnedByMonth(y, m)
  return monthWeeks.some(w => {
    const yearWeeks = availableWeeksData.value[w.isoYear] || []
    return yearWeeks.includes(w.isoWeek)
  })
}

// 检查某周是否有数据（参数是当月第几周）
const weekHasData = (y, m, weekOfM) => {
  const weekInfo = getActualWeekInfo(y, m, weekOfM)
  const yearWeeks = availableWeeksData.value[weekInfo.isoYear] || []
  return yearWeeks.includes(weekInfo.isoWeek)
}

// 检查某周是否已经到达（周一已经过了）
const weekHasArrived = (y, m, weekOfM) => {
  const weekInfo = getActualWeekInfo(y, m, weekOfM)
  const monday = getMondayOfWeek(weekInfo.isoYear, weekInfo.isoWeek)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return monday <= today
}

// 检查某月是否已经到达（该月至少有一周已到达）
const monthHasArrived = (y, m) => {
  const weeks = getWeeksOwnedByMonth(y, m)
  if (weeks.length === 0) return false
  const firstWeekMonday = getMondayOfWeek(weeks[0].isoYear, weeks[0].isoWeek)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return firstWeekMonday <= today
}

// 可显示的周列表（已到达的周）
const displayableWeeksOfMonth = computed(() => {
  return availableWeeksOfMonth.value.filter(w => weekHasArrived(year.value, month.value, w))
})

// 检查某年是否已经到达（当前年份及之前的年份）
const yearHasArrived = (y) => {
  return y <= currentYear
}

// 可显示的年份列表（已到达的年份）
const displayableYears = computed(() => {
  return availableYears.filter(y => yearHasArrived(y))
})

// 可显示的月份（已到达的月份，1-12）
const displayableMonths = computed(() => {
  const months = []
  for (let m = 1; m <= 12; m++) {
    if (monthHasArrived(year.value, m)) {
      months.push(m)
    }
  }
  return months
})

// 获取有提交内容的最新周
const fetchLatestWeek = async () => {
  try {
    const res = await summaryApi.getLatestWeek()
    if (res.data) {
      const isoYear = res.data.year
      const isoWeek = res.data.week
      // 根据ISO年和周数找到所属月份（周一所在的月份）
      const { year: displayYear, month: displayMonth } = getMonthOfISOWeek(isoYear, isoWeek)
      year.value = displayYear
      month.value = displayMonth
      // 计算是当月第几周
      weekOfMonth.value = getWeekOfMonthFromISO(displayYear, displayMonth, isoYear, isoWeek)
    }
  } catch (e) {
    console.error('获取最新周失败', e)
  }
}

const dashboardData = ref(null)
const summaryData = ref(null)
const loading = ref(false)
const availableWeeksData = ref({})  // {year: [week1, week2, ...]}

// 图表DOM引用
const memberTaskChartRef = ref(null)
const projectChartRef = ref(null)
const categoryChartRef = ref(null)

let memberTaskChart = null
let projectChart = null
let categoryChart = null

// v0.app 风格配色方案
const colors = ['#7aaed8', '#5a92d1', '#3da89a', '#8fb84a', '#d4a73a', '#dc8044', '#d46a6a', '#ab7ed0', '#9683ce', '#3aacb8', '#4db06a', '#dc9a3d']

const fetchDashboard = async () => {
  loading.value = true
  try {
    const [dashRes, summRes] = await Promise.all([
      summaryApi.getDashboard(actualYear.value, week.value),
      summaryApi.getWeekly(actualYear.value, week.value)
    ])
    dashboardData.value = dashRes.data
    summaryData.value = summRes.data
    setTimeout(updateCharts, 100)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const downloadWord = async () => {
  try {
    const response = await summaryApi.downloadWord(actualYear.value, week.value)
    const blob = new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `周报_${actualYear.value}年第${week.value}周.docx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

const updateCharts = () => {
  if (!dashboardData.value) return

  const { member_tasks, project_involvement, work_categories } = dashboardData.value

  // 各成员任务分布柱状图
  if (memberTaskChart && member_tasks) {
    memberTaskChart.setOption({
      grid: { left: 40, right: 20, top: 20, bottom: 30 },
      xAxis: {
        type: 'category',
        data: member_tasks.map(m => m.name),
        axisLabel: { color: '#666', fontSize: 11 },
        axisLine: { lineStyle: { color: '#ddd' } }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#999', fontSize: 10 },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      series: [{
        type: 'bar',
        data: member_tasks.map((m, i) => ({
          value: m.task_count,
          itemStyle: { color: colors[i % colors.length], borderRadius: [4, 4, 0, 0] }
        })),
        barWidth: '50%'
      }]
    })
  }

  // 项目参与情况饼状图
  if (projectChart && project_involvement) {
    projectChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { fontSize: 11, color: '#666' }
      },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold'
          }
        },
        data: project_involvement.map((p, i) => ({
          ...p,
          itemStyle: { color: colors[i % colors.length] }
        }))
      }]
    })
  }

  // 工作类型分布饼图
  if (categoryChart && work_categories) {
    categoryChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        textStyle: { fontSize: 11, color: '#666' }
      },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        label: {
          show: true,
          position: 'outside',
          formatter: '{d}%',
          fontSize: 10,
          color: '#666'
        },
        labelLine: {
          show: true,
          length: 8,
          length2: 5
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 12,
            fontWeight: 'bold'
          }
        },
        data: work_categories.map((c, i) => ({
          ...c,
          itemStyle: { color: colors[i % colors.length] }
        }))
      }]
    })
  }
}

const initCharts = () => {
  memberTaskChart?.dispose()
  projectChart?.dispose()
  categoryChart?.dispose()

  memberTaskChart = null
  projectChart = null
  categoryChart = null

  if (memberTaskChartRef.value) {
    memberTaskChart = echarts.init(memberTaskChartRef.value)
  }
  if (projectChartRef.value) {
    projectChart = echarts.init(projectChartRef.value)
  }
  if (categoryChartRef.value) {
    categoryChart = echarts.init(categoryChartRef.value)
  }
}

const handleResize = () => {
  memberTaskChart?.resize()
  projectChart?.resize()
  categoryChart?.resize()
}

// 选择年份
const selectYear = (y) => {
  year.value = y
  // 重置月份和周
  month.value = 1
  weekOfMonth.value = 1
}

// 选择月份
const selectMonth = (m) => {
  month.value = m
  // 重置周为该月第一周
  weekOfMonth.value = 1
}

// 选择周（当月第几周）
const selectWeek = (w) => {
  weekOfMonth.value = w
}

onMounted(async () => {
  await fetchAvailableWeeks()
  await fetchLatestWeek()
  nextTick(() => {
    initCharts()
    fetchDashboard()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  memberTaskChart?.dispose()
  projectChart?.dispose()
  categoryChart?.dispose()
})

watch([year, month, weekOfMonth], fetchDashboard)
</script>

<template>
  <div class="dashboard-page">
    <!-- 标题区域 -->
    <div class="dashboard-header">
      <h1 class="title">产品研发部工作周报</h1>

      <!-- 年月周标签选择器 -->
      <div class="time-selector">
        <!-- 年份选择 -->
        <div class="selector-row">
          <span class="selector-label">年份</span>
          <div class="tag-group">
            <button
              v-for="y in displayableYears"
              :key="y"
              class="tag-btn"
              :class="{ active: year === y, disabled: !yearHasData(y) }"
              :disabled="!yearHasData(y)"
              @click="yearHasData(y) && selectYear(y)"
            >
              {{ y }}年
            </button>
          </div>
        </div>

        <!-- 月份选择 -->
        <div class="selector-row">
          <span class="selector-label">月份</span>
          <div class="tag-group">
            <button
              v-for="m in displayableMonths"
              :key="m"
              class="tag-btn"
              :class="{ active: month === m, disabled: !monthHasData(year, m) }"
              :disabled="!monthHasData(year, m)"
              @click="monthHasData(year, m) && selectMonth(m)"
            >
              {{ m }}月
            </button>
          </div>
        </div>

        <!-- 周选择（当月第几周） -->
        <div class="selector-row">
          <span class="selector-label">周次</span>
          <div class="tag-group">
            <button
              v-for="w in displayableWeeksOfMonth"
              :key="w"
              class="tag-btn"
              :class="{ active: weekOfMonth === w, disabled: !weekHasData(year, month, w) }"
              :disabled="!weekHasData(year, month, w)"
              @click="weekHasData(year, month, w) && selectWeek(w)"
            >
              第{{ w }}周
            </button>
          </div>
        </div>

      </div>

      <p class="date-range" v-if="dashboardData">{{ dashboardData.date_range }}</p>

      <!-- 下载按钮 -->
      <div class="action-bar">
        <button class="download-btn" @click="downloadWord" :disabled="!summaryData?.reports?.length">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
          </svg>
          下载Word
        </button>
      </div>
    </div>

    <div v-loading="loading" class="dashboard-content">
      <!-- 统计卡片 -->
      <div class="stats-row" v-if="dashboardData">
        <div class="stat-card">
          <div class="stat-value">{{ dashboardData.stats.total_members }}</div>
          <div class="stat-label">团队成员</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ dashboardData.stats.total_tasks }}</div>
          <div class="stat-label">本周任务数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ dashboardData.stats.completion_rate }}%</div>
          <div class="stat-label">完成率</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ dashboardData.stats.main_projects_count }}</div>
          <div class="stat-label">主要项目</div>
        </div>
      </div>

      <!-- 图表区域第一行 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 20V10M12 20V4M6 20v-6"/>
            </svg>
            <span class="card-title">各成员任务分布</span>
          </div>
          <div ref="memberTaskChartRef" class="chart-container"></div>
        </div>
        <div class="chart-card">
          <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.21 15.89A10 10 0 118 2.83"/>
              <path d="M22 12A10 10 0 0012 2v10z"/>
            </svg>
            <span class="card-title">项目参与情况</span>
          </div>
          <div ref="projectChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 图表区域第二行 -->
      <div class="chart-row">
        <div class="chart-card">
          <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
              <rect x="9" y="3" width="6" height="4" rx="1"/>
              <path d="M9 12h6M9 16h6"/>
            </svg>
            <span class="card-title">主要项目进展</span>
          </div>
          <div class="project-list" v-if="dashboardData">
            <div
              v-for="(proj, index) in dashboardData.main_projects"
              :key="proj"
              class="project-item"
            >
              <span class="project-dot" :style="{ background: colors[index % colors.length] }"></span>
              <span class="project-name">{{ proj }}</span>
            </div>
            <div v-if="!dashboardData.main_projects?.length" class="empty-text">暂无项目数据</div>
          </div>
        </div>
        <div class="chart-card">
          <div class="card-header">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
            <span class="card-title">工作类型分布</span>
          </div>
          <div ref="categoryChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 团队成员工作详情 -->
      <div class="detail-card" v-if="summaryData?.reports?.length">
        <div class="card-header">
          <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
          </svg>
          <span class="card-title">团队成员本周工作详情</span>
        </div>
        <table class="detail-table">
          <thead>
            <tr>
              <th style="width: 80px">成员</th>
              <th>本周工作</th>
              <th style="width: 80px">任务数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in summaryData.reports" :key="report.user_id">
              <td class="member-name">{{ report.user_name }}</td>
              <td class="work-cell">
                <div class="work-content-lines">{{ report.this_week_work }}</div>
              </td>
              <td class="task-count">
                <span class="count-badge">{{ report.task_count }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 下周工作计划 -->
      <div class="detail-card" v-if="summaryData?.reports?.length">
        <div class="card-header">
          <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2"/>
            <path d="M16 2v4M8 2v4M3 10h18"/>
          </svg>
          <span class="card-title">下周工作计划</span>
        </div>
        <table class="detail-table">
          <thead>
            <tr>
              <th style="width: 80px">成员</th>
              <th>计划内容</th>
              <th style="width: 80px">计划数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in summaryData.reports" :key="report.user_id + '-next'">
              <td class="member-name">{{ report.user_name }}</td>
              <td class="work-cell">
                <div class="work-content-lines">{{ report.next_week_plan || '暂无计划' }}</div>
              </td>
              <td class="task-count">
                <span class="count-badge">{{ (report.next_week_plan || '').split('\n').filter(l => l.trim()).length }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-if="!loading && !summaryData?.reports?.length">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 12h-6l-2 3h-4l-2-3H2"/>
          <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>
        </svg>
        <p>该周暂无已提交的周报</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* v0.app 风格 - 现代简洁设计 */
.dashboard-page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 24px;
  margin: -20px;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 32px;
  padding: 32px 24px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
}

.title {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 24px;
  letter-spacing: -0.025em;
}

/* 时间选择器 - 标签多级点选 */
.time-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}

.selector-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.selector-label {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  min-width: 48px;
  text-align: right;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-btn {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag-btn:hover {
  border-color: #7aaed8;
  color: #7aaed8;
}

.tag-btn.active {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #64748b;
}

.tag-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #7aaed8;
}

.tag-btn.disabled:hover {
  border-color: #e2e8f0;
  color: #7aaed8;
}


.date-range {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 20px;
}

/* 操作按钮区 */
.action-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 10px;
  background: #10b981;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.download-btn:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #7aaed8;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-card:nth-child(2) .stat-value {
  color: #06b6d4;
}

.stat-card:nth-child(3) .stat-value {
  color: #10b981;
}

.stat-card:nth-child(4) .stat-value {
  color: #f59e0b;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

/* 图表区域 */
.chart-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

.chart-card, .detail-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.detail-card {
  margin-bottom: 16px;
}

.chart-row .chart-card {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
}

.chart-row .chart-card .chart-container,
.chart-row .chart-card .project-list {
  flex: 1;
}

.detail-card .card-header {
  border-bottom: none;
  padding-bottom: 0;
  margin-bottom: 12px;
}

.chart-card:last-child, .detail-card:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.card-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: #7aaed8;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.chart-container {
  flex: 1;
  min-height: 220px;
}

/* 项目列表 */
.project-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 8px 0;
  flex: 1;
  min-height: 220px;
  align-content: start;
}

.project-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  transition: background 0.2s;
}

.project-item:hover {
  background: #f1f5f9;
}

.project-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.project-name {
  font-size: 14px;
  color: #334155;
  font-weight: 500;
}

.empty-text {
  color: #7aaed8;
  font-size: 14px;
  grid-column: span 2;
  text-align: center;
  padding: 24px;
}

/* 详情表格 */
.detail-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.detail-table thead {
  background: #f8fafc;
}

.detail-table th {
  color: #475569;
  font-weight: 600;
  font-size: 13px;
  padding: 14px 16px;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e2e8f0;
}

.detail-table td {
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
  color: #334155;
}

.detail-table tbody tr:hover {
  background: #f8fafc;
}

.member-name {
  font-weight: 600;
  color: #0f172a;
}

.work-cell {
  vertical-align: top;
}

.work-content-lines {
  white-space: pre-line;
  line-height: 1.8;
  font-size: 14px;
  color: #475569;
  padding: 4px 0;
}

.task-count {
  text-align: center;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  background: #e8f4fa;
  color: #7aaed8;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #7aaed8;
}

.empty-state p {
  font-size: 16px;
  color: #64748b;
}

/* 响应式 */
@media (max-width: 1024px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 16px;
  }

  .dashboard-header {
    padding: 20px 16px;
  }

  .title {
    font-size: 1.5rem;
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .stat-card {
    padding: 16px;
  }

  .stat-value {
    font-size: 1.75rem;
  }

  .chart-row {
    grid-template-columns: 1fr;
  }

  .project-list {
    grid-template-columns: 1fr;
  }

  .selector-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .selector-label {
    text-align: left;
  }
}
</style>
