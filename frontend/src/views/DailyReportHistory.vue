<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { dailyReportApi } from '../api/dailyReport'
import { ElMessage } from 'element-plus'

const router = useRouter()

const reports = ref([])
const isLoading = ref(true)

// 日期范围选择
const dateRange = ref([])

// 默认显示最近30天
const initDateRange = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  dateRange.value = [start, end]
}

// 格式化日期
const formatDate = (date) => {
  if (!date) return ''
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 获取星期几
const getWeekDay = (date) => {
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return days[new Date(date).getDay()]
}

// 格式化显示日期
const formatDisplayDate = (dateStr) => {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${getWeekDay(dateStr)}`
}

// 加载日报列表
const loadReports = async () => {
  if (!dateRange.value || dateRange.value.length !== 2) return

  isLoading.value = true
  try {
    const [start, end] = dateRange.value
    reports.value = await dailyReportApi.getList(formatDate(start), formatDate(end))
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    isLoading.value = false
  }
}

// 按周分组日报
const groupedReports = computed(() => {
  const groups = {}

  reports.value.forEach(report => {
    const d = new Date(report.date)
    // 获取ISO周的周一
    const dayOfWeek = d.getDay() || 7
    const monday = new Date(d)
    monday.setDate(d.getDate() - (dayOfWeek - 1))
    const weekKey = formatDate(monday)

    if (!groups[weekKey]) {
      const sunday = new Date(monday)
      sunday.setDate(monday.getDate() + 6)
      groups[weekKey] = {
        weekStart: monday,
        weekEnd: sunday,
        reports: [],
        totalHours: 0
      }
    }

    groups[weekKey].reports.push(report)

    // 计算总工时
    report.items?.forEach(item => {
      if (item.hours) {
        groups[weekKey].totalHours += parseFloat(item.hours)
      }
    })
  })

  // 按周排序（最近的在前）
  return Object.entries(groups)
    .sort((a, b) => new Date(b[0]) - new Date(a[0]))
    .map(([key, value]) => value)
})

// 计算单个日报的工时
const getReportHours = (report) => {
  return report.items?.reduce((sum, item) => sum + (parseFloat(item.hours) || 0), 0) || 0
}

// 跳转到编辑页面
const goToEdit = (report) => {
  router.push({
    path: '/daily-report',
    query: { date: report.date }
  })
}

// 日期范围变化
const handleDateRangeChange = () => {
  loadReports()
}

// 快捷选择
const shortcuts = [
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      return [start, end]
    }
  },
  {
    text: '本月',
    value: () => {
      const end = new Date()
      const start = new Date(end.getFullYear(), end.getMonth(), 1)
      return [start, end]
    }
  },
  {
    text: '上月',
    value: () => {
      const end = new Date()
      end.setDate(0) // 上月最后一天
      const start = new Date(end.getFullYear(), end.getMonth(), 1)
      return [start, end]
    }
  }
]

onMounted(() => {
  initDateRange()
  loadReports()
})
</script>

<template>
  <div class="history-container">
    <el-card>
      <template #header>
        <div class="header-content">
          <h2>日报历史</h2>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            :shortcuts="shortcuts"
            @change="handleDateRangeChange"
          />
        </div>
      </template>

      <div v-loading="isLoading">
        <el-empty v-if="!reports.length && !isLoading" description="暂无日报记录" />

        <div v-else class="report-groups">
          <div v-for="(group, index) in groupedReports" :key="index" class="week-group">
            <div class="week-header">
              <span class="week-range">
                {{ formatDisplayDate(formatDate(group.weekStart)) }} -
                {{ formatDisplayDate(formatDate(group.weekEnd)) }}
              </span>
              <span class="week-stats">
                {{ group.reports.length }} 天 |
                总工时: {{ group.totalHours.toFixed(1) }} 小时
              </span>
            </div>

            <div class="report-list">
              <div
                v-for="report in group.reports"
                :key="report.id"
                class="report-item"
                @click="goToEdit(report)"
              >
                <div class="report-date">
                  <span class="date-text">{{ formatDisplayDate(report.date) }}</span>
                  <span class="hours-badge" v-if="getReportHours(report) > 0">
                    {{ getReportHours(report).toFixed(1) }}h
                  </span>
                </div>

                <div class="report-content">
                  <div v-if="report.items?.length" class="item-list">
                    <div v-for="item in report.items" :key="item.id" class="work-item">
                      <el-tag v-if="item.project_name" type="info" size="small">
                        {{ item.project_name }}
                      </el-tag>
                      <span class="item-content">{{ item.content }}</span>
                      <span v-if="item.hours" class="item-hours">{{ item.hours }}h</span>
                    </div>
                  </div>
                  <div v-else class="raw-content">
                    {{ report.work_content || '无内容' }}
                  </div>
                </div>

                <div class="report-meta">
                  <span :class="['edit-status', report.editable ? 'editable' : 'locked']">
                    {{ report.editable ? '可编辑' : '已锁定' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.history-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h2 {
  margin: 0;
  font-size: 20px;
}

.report-groups {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.week-group {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
}

.week-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.week-range {
  font-weight: 600;
  color: #303133;
}

.week-stats {
  color: #909399;
  font-size: 13px;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-item {
  background: white;
  border-radius: 6px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.report-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.report-date {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.date-text {
  font-weight: 500;
  color: #303133;
}

.hours-badge {
  background: #ecf5ff;
  color: #409eff;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.report-content {
  margin-bottom: 8px;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.work-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.item-content {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-hours {
  color: #909399;
  font-size: 12px;
  flex-shrink: 0;
}

.raw-content {
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-meta {
  display: flex;
  justify-content: flex-end;
}

.edit-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.edit-status.editable {
  background: #f0f9eb;
  color: #67c23a;
}

.edit-status.locked {
  background: #fef0f0;
  color: #f56c6c;
}
</style>
