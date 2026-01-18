<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDailyReportStore } from '../stores/dailyReport'
import { dailyReportApi } from '../api/dailyReport'
import { reportApi } from '../api/report'
import { taskApi } from '../api/task'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const dailyReportStore = useDailyReportStore()

// 选择的日期
const selectedDate = ref(new Date())
const isLoading = ref(true)

// 项目列表
const projectList = ref([])

// 任务列表（进行中的任务）
const taskList = ref([])

// 本周日报概览
const weekReports = ref([])

// 工作条目列表
const workItems = ref([])

// 创建空的工作条目
const createEmptyItem = () => ({
  task_id: null,
  project_name: null,
  content: '',
  hours: null,
  progress: 50,           // 状态：0=未开始，50=进行中，100=已完成
  task_progress: null,    // 任务进度更新
  remark: ''
})

// 格式化日期为 YYYY-MM-DD
const formatDate = (date) => {
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 获取星期几
const getWeekDay = (date) => {
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return days[new Date(date).getDay()]
}

// 当前选择日期的格式化显示
const dateDisplay = computed(() => {
  const d = new Date(selectedDate.value)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${getWeekDay(d)}`
})

// 完整日期显示（带星期几）
const dateDisplayFull = computed(() => {
  const d = new Date(selectedDate.value)
  const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日${weekDays[d.getDay()]}`
})

// 全局备注
const globalRemark = ref('')

// 是否可编辑
const canEdit = computed(() => {
  return dailyReportStore.currentReport?.editable !== false
})

// 是否有现有日报
const hasExistingReport = computed(() => !!dailyReportStore.currentReport?.id)

// 总工时
const totalHours = computed(() => {
  return workItems.value.reduce((sum, item) => sum + (parseFloat(item.hours) || 0), 0)
})

// 活跃项目（最近30天有使用）
const activeProjects = computed(() => {
  return projectList.value.filter(p => p.is_active)
})

// 不活跃项目
const inactiveProjects = computed(() => {
  return projectList.value.filter(p => !p.is_active)
})

// 禁用未来日期
const disableFutureDate = (date) => {
  return date > new Date()
}

// 获取本周的起止日期（周一到周日）
const getWeekRange = () => {
  const today = new Date()
  const dayOfWeek = today.getDay() || 7
  const monday = new Date(today)
  monday.setDate(today.getDate() - (dayOfWeek - 1))
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return { monday, sunday }
}

// 加载日报数据
const loadDailyReport = async () => {
  isLoading.value = true
  const dateStr = formatDate(selectedDate.value)

  try {
    await dailyReportStore.fetchReportByDate(dateStr)

    if (dailyReportStore.currentReport) {
      // 加载已有的条目
      if (dailyReportStore.currentReport.items?.length > 0) {
        workItems.value = dailyReportStore.currentReport.items.map(item => ({
          task_id: item.task_id || null,
          project_name: item.project_name,
          content: item.content,
          hours: item.hours != null ? Number(item.hours) : null,
          progress: item.progress != null ? Number(item.progress) : 50,
          task_progress: item.task_progress != null ? Number(item.task_progress) : null,
          remark: item.remark || ''
        }))
      } else {
        workItems.value = [createEmptyItem()]
      }
    } else {
      workItems.value = [createEmptyItem()]
    }
  } finally {
    isLoading.value = false
  }
}

// 加载本周日报概览
const loadWeekOverview = async () => {
  const { monday, sunday } = getWeekRange()
  const reports = await dailyReportApi.getList(formatDate(monday), formatDate(sunday))
  weekReports.value = reports || []
}

// 监听日期变化
watch(selectedDate, async () => {
  dailyReportStore.resetCurrentReport()
  await loadDailyReport()
})

// 加载任务列表
const loadTasks = async () => {
  try {
    taskList.value = await taskApi.getMyTasks()
  } catch (e) {
    console.error('加载任务列表失败')
  }
}

// 根据项目筛选任务列表
const getFilteredTasks = (projectName) => {
  if (!projectName) {
    return taskList.value
  }
  return taskList.value.filter(t => t.project_name === projectName)
}

// 选择任务时的处理（自动填充项目）
const handleTaskSelect = (index, taskId) => {
  const item = workItems.value[index]
  if (taskId) {
    const task = taskList.value.find(t => t.id === taskId)
    if (task) {
      // 自动填充项目名称
      if (task.project_name) {
        item.project_name = task.project_name
      }
      // 设置初始任务进度为当前任务进度
      item.task_progress = task.progress
    }
  } else {
    // 取消选择任务时，清空任务进度
    item.task_progress = null
  }
}

// 选择项目时的处理（筛选任务列表）
const handleProjectChange = (index, projectName) => {
  const item = workItems.value[index]
  // 如果当前选择的任务不属于新项目，清空任务选择
  if (item.task_id) {
    const currentTask = taskList.value.find(t => t.id === item.task_id)
    if (currentTask && currentTask.project_name !== projectName) {
      item.task_id = null
      item.task_progress = null
    }
  }
}

// 获取任务信息
const getTaskInfo = (taskId) => {
  return taskList.value.find(t => t.id === taskId)
}

onMounted(async () => {
  // 检查URL参数中是否有指定日期
  if (route.query.date) {
    selectedDate.value = new Date(route.query.date)
  }

  const [_, projects] = await Promise.all([
    loadDailyReport(),
    reportApi.getProjects().catch(() => []),
    loadTasks()
  ])
  projectList.value = projects || []
  await loadWeekOverview()
})

// 添加工作条目
const addWorkItem = () => {
  workItems.value.push(createEmptyItem())
}

// 删除工作条目
const removeWorkItem = (index) => {
  if (workItems.value.length > 1) {
    workItems.value.splice(index, 1)
  } else {
    ElMessage.warning('至少保留一条工作记录')
  }
}

// 保存日报
const handleSave = async () => {
  // 验证：至少有一条有效内容
  const validItems = workItems.value.filter(item => item.content?.trim())
  if (validItems.length === 0) {
    ElMessage.warning('请填写至少一条工作内容')
    return
  }

  try {
    const payload = {
      date: formatDate(selectedDate.value),
      work_content: null, // 结构化输入不需要原始文本
      items: validItems.map((item, index) => ({
        task_id: item.task_id || null,
        project_name: item.project_name,
        content: item.content.trim(),
        hours: item.hours || null,
        progress: item.progress,
        task_progress: item.task_id ? item.task_progress : null, // 只有关联任务时才传任务进度
        remark: item.remark?.trim() || null
      }))
    }

    await dailyReportStore.saveReport(payload)
    ElMessage.success('保存成功')
    // 刷新任务列表（任务进度可能已更新）
    await loadTasks()
    await loadWeekOverview()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

// 删除日报
const handleDelete = async () => {
  if (!dailyReportStore.currentReport?.id) return

  try {
    await ElMessageBox.confirm('确定要删除这份日报吗？', '确认删除', {
      type: 'warning'
    })

    await dailyReportStore.deleteReport(dailyReportStore.currentReport.id)
    workItems.value = [createEmptyItem()]
    ElMessage.success('已删除')
    await loadWeekOverview()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

// 重置表单
const handleReset = () => {
  workItems.value = [createEmptyItem()]
  ElMessage.info('已重置')
}

// 获取某天的日报状态
const getDayStatus = (dayOffset) => {
  const { monday } = getWeekRange()
  const targetDate = new Date(monday)
  targetDate.setDate(monday.getDate() + dayOffset)
  const dateStr = formatDate(targetDate)
  const today = formatDate(new Date())

  const report = weekReports.value.find(r => r.date === dateStr)

  if (report) {
    return { status: 'submitted', date: targetDate }
  } else if (dateStr === formatDate(selectedDate.value) && workItems.value.some(item => item.content?.trim())) {
    return { status: 'editing', date: targetDate }
  } else if (dateStr > today) {
    return { status: 'future', date: targetDate }
  } else {
    return { status: 'empty', date: targetDate }
  }
}

// 快速切换日期
const switchToDate = (date) => {
  if (date <= new Date()) {
    selectedDate.value = date
  }
}

// 状态选项（映射到 progress 字段：0=未开始，50=进行中，100=已完成）
const statusOptions = [
  { label: '未开始', value: 0, icon: 'not-started', color: '#7aaed8' },
  { label: '进行中', value: 50, icon: 'in-progress', color: '#f59e0b' },
  { label: '已完成', value: 100, icon: 'completed', color: '#10b981' }
]
</script>

<template>
  <div class="page-container">
    <div class="page-content" v-loading="isLoading">
      <!-- 页面头部卡片 -->
      <div class="header-card">
        <div class="header-left">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <div class="header-info">
            <h1 class="header-title">填写日报</h1>
            <div class="header-date">
              <span>{{ dateDisplayFull }}</span>
              <el-date-picker
                v-model="selectedDate"
                type="date"
                placeholder="选择日期"
                :disabled-date="disableFutureDate"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                :clearable="false"
                size="small"
                class="date-picker-inline"
              />
            </div>
          </div>
        </div>
        <div class="header-stats">
          <div class="stat-box">
            <span class="stat-number">{{ workItems.filter(i => i.content?.trim()).length }}</span>
            <span class="stat-label">工作项</span>
          </div>
          <div class="stat-box highlight">
            <span class="stat-number">{{ totalHours > 0 ? totalHours + 'h' : '0h' }}</span>
            <span class="stat-label">总工时</span>
          </div>
        </div>
      </div>

      <!-- 主内容区域 -->
      <div class="main-area">
        <!-- 左侧：工作内容 -->
        <div class="work-section">
          <!-- 工作内容卡片 -->
          <div class="content-card">
            <div class="card-header">
              <div class="card-title-group">
                <h2 class="card-title">今日工作内容</h2>
                <p class="card-subtitle">逐条记录今日完成的工作</p>
              </div>
              <button class="btn-add-item" @click="addWorkItem" :disabled="!canEdit">
                <span class="btn-icon">+</span>
                <span>添加工作项</span>
              </button>
            </div>

            <!-- 工作项列表 -->
            <div class="work-items">
              <div
                v-for="(item, index) in workItems"
                :key="index"
                class="work-item"
              >
                <!-- 删除按钮 - 右上角绝对定位 -->
                <button
                  v-if="workItems.length > 1"
                  class="btn-delete-item"
                  @click="removeWorkItem(index)"
                  :disabled="!canEdit"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                  </svg>
                </button>

                <div class="item-header">
                  <div class="item-title">
                    <span class="item-index">{{ index + 1 }}</span>
                    <span>工作项 {{ index + 1 }}</span>
                  </div>
                  <div class="item-header-right">
                    <!-- 项目选择 -->
                    <el-select
                      v-model="item.project_name"
                      placeholder="选择项目"
                      clearable
                      filterable
                      size="small"
                      class="project-select"
                      :disabled="!canEdit"
                      @change="(val) => handleProjectChange(index, val)"
                    >
                      <el-option-group label="常用项目" v-if="activeProjects.length > 0">
                        <el-option
                          v-for="project in activeProjects"
                          :key="project.name"
                          :label="project.name"
                          :value="project.name"
                        />
                      </el-option-group>
                      <el-option-group label="其他项目" v-if="inactiveProjects.length > 0">
                        <el-option
                          v-for="project in inactiveProjects"
                          :key="project.name"
                          :label="project.name"
                          :value="project.name"
                        />
                      </el-option-group>
                    </el-select>
                    <!-- 任务选择（根据项目筛选） -->
                    <el-select
                      v-model="item.task_id"
                      placeholder="关联任务（可选）"
                      clearable
                      size="small"
                      class="task-select"
                      :disabled="!canEdit"
                      @change="(val) => handleTaskSelect(index, val)"
                    >
                      <el-option
                        v-for="task in getFilteredTasks(item.project_name)"
                        :key="task.id"
                        :label="task.title"
                        :value="task.id"
                      >
                        <div class="task-option">
                          <span class="task-option-title">{{ task.title }}</span>
                          <span class="task-option-progress">{{ task.progress }}%</span>
                        </div>
                      </el-option>
                    </el-select>
                  </div>
                </div>

                <!-- 工作内容输入 -->
                <div class="form-group">
                  <label class="form-label">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                      <polyline points="14,2 14,8 20,8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    工作内容
                  </label>
                  <el-input
                    v-model="item.content"
                    type="textarea"
                    :rows="3"
                    placeholder="请描述今日完成的具体工作内容..."
                    :disabled="!canEdit"
                  />
                </div>

                <!-- 工时和进度 -->
                <div class="form-row">
                  <div class="form-group hours-group">
                    <label class="form-label">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <polyline points="12,6 12,12 16,14"/>
                      </svg>
                      工时 (小时)
                    </label>
                    <div class="hours-input-row">
                      <el-input-number
                        v-model="item.hours"
                        :min="0"
                        :max="12"
                        :step="0.5"
                        :precision="1"
                        controls-position="right"
                        :disabled="!canEdit"
                        class="hours-input"
                      />
                      <div class="hours-quick-btns">
                        <button
                          v-for="h in [1, 2, 4, 8]"
                          :key="h"
                          class="quick-hour-btn"
                          :class="{ active: item.hours === h }"
                          @click="item.hours = h"
                          :disabled="!canEdit"
                        >{{ h }}h</button>
                      </div>
                    </div>
                  </div>

                  <div class="form-group status-group">
                    <label class="form-label">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 11l3 3L22 4"/>
                        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
                      </svg>
                      完成状态
                    </label>
                    <div class="status-buttons">
                      <button
                        v-for="opt in statusOptions"
                        :key="opt.value"
                        class="status-btn"
                        :class="[
                          opt.icon,
                          { active: item.progress === opt.value }
                        ]"
                        @click="item.progress = opt.value"
                        :disabled="!canEdit"
                      >
                        <!-- 未开始：空心圆 -->
                        <span v-if="opt.icon === 'not-started'" class="status-icon-circle" :class="{ active: item.progress === opt.value }"></span>
                        <!-- 进行中：半实心圆 -->
                        <span v-else-if="opt.icon === 'in-progress'" class="status-icon-half" :class="{ active: item.progress === opt.value }"></span>
                        <!-- 已完成：实心圆+勾选 -->
                        <span v-else-if="opt.icon === 'completed'" class="status-icon-check" :class="{ active: item.progress === opt.value }">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                            <path d="M6 12l4 4 8-8" stroke-linecap="round" stroke-linejoin="round"/>
                          </svg>
                        </span>
                        <span>{{ opt.label }}</span>
                      </button>
                    </div>
                  </div>
                </div>

                <!-- 任务进度更新（仅关联任务时显示） -->
                <div class="task-progress-row" v-if="item.task_id">
                  <label class="form-label">
                    <span class="progress-label-left">
                      <span class="percent-icon">%</span>
                      <span>任务进度 · <span class="task-name">{{ getTaskInfo(item.task_id)?.title }}</span></span>
                    </span>
                    <span class="progress-value">{{ item.task_progress ?? getTaskInfo(item.task_id)?.progress ?? 0 }}%</span>
                  </label>
                  <div class="progress-slider-wrapper">
                    <el-slider
                      v-model="item.task_progress"
                      :min="0"
                      :max="100"
                      :step="5"
                      :show-tooltip="false"
                      :disabled="!canEdit"
                    />
                    <div class="progress-labels">
                      <span>0%</span>
                      <span>50%</span>
                      <span>100%</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            <!-- 备注说明 -->
            <div class="remark-section">
              <label class="form-label">备注说明（可选）</label>
              <el-input
                v-model="globalRemark"
                type="textarea"
                :rows="3"
                placeholder="如有需要协调的事项、遇到的问题或其他说明，请在此填写..."
                :disabled="!canEdit"
              />
            </div>

            <!-- 分割线 -->
            <div class="card-divider"></div>

            <!-- 操作按钮 -->
            <div class="action-bar">
              <button class="btn btn-secondary" @click="handleReset" :disabled="!canEdit">
                重置
              </button>
              <button
                v-if="hasExistingReport"
                class="btn btn-danger"
                @click="handleDelete"
                :disabled="!canEdit"
              >
                删除日报
              </button>
              <button
                class="btn btn-primary"
                @click="handleSave"
                :disabled="!canEdit"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22,2 15,22 11,13 2,9 22,2"/>
                </svg>
                {{ hasExistingReport ? '更新日报' : '提交日报' }}
              </button>
            </div>
          </div>

          <!-- 不可编辑提示 -->
          <div class="locked-notice" v-if="!canEdit">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0110 0v4"/>
            </svg>
            <span>该日报已超过可修改时间</span>
          </div>
        </div>

        <!-- 右侧：本周概览 -->
        <div class="week-overview">
          <div class="overview-card">
            <div class="overview-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
              <span>本周概览</span>
            </div>
            <div class="week-days">
              <div
                v-for="(day, index) in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
                :key="index"
                class="day-item"
                :class="{ selected: formatDate(getDayStatus(index).date) === formatDate(selectedDate), future: getDayStatus(index).status === 'future' }"
                @click="switchToDate(getDayStatus(index).date)"
              >
                <span class="day-name">{{ day }}</span>
                <span class="day-status-icon" :class="formatDate(getDayStatus(index).date) === formatDate(selectedDate) ? 'editing' : getDayStatus(index).status">
                  <template v-if="formatDate(getDayStatus(index).date) === formatDate(selectedDate)"><span class="editing-dot"></span></template>
                  <template v-else-if="getDayStatus(index).status === 'submitted'">
                    <span class="check-circle">
                      <svg viewBox="0 0 24 24" fill="none">
                        <path d="M8 12l3 3 5-6" stroke="#7aaed8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>
                    </span>
                  </template>
                  <template v-else-if="getDayStatus(index).status === 'future'">—</template>
                  <template v-else>○</template>
                </span>
              </div>
            </div>
            <div class="overview-legend">
              <div class="legend-item">
                <span class="legend-check-circle">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M8 12l3 3 5-6" stroke="#7aaed8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
                已填写
              </div>
              <div class="legend-item"><span class="dot editing"></span>编辑中</div>
              <div class="legend-item"><span class="dot empty"></span>未填写</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.page-container {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #f5f7fa;
}

.page-content {
  max-width: 1100px;
  margin: 0 auto;
}

/* 头部卡片 */
.header-card {
  background: white;
  border-radius: 16px;
  padding: 24px 32px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  background: #e8f4fc;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-icon svg {
  width: 24px;
  height: 24px;
  color: #7aaed8;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.header-date {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.date-picker-inline {
  width: 32px !important;
}

.date-picker-inline :deep(.el-input__wrapper) {
  padding: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}

.date-picker-inline :deep(.el-input__inner) {
  display: none;
}

.date-picker-inline :deep(.el-input__prefix) {
  color: #7aaed8;
  cursor: pointer;
}

.header-stats {
  display: flex;
  gap: 12px;
}

.stat-box {
  min-width: 80px;
  padding: 12px 20px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-box.highlight {
  border-color: #fcd9b6;
  background: #fffaf5;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: #7aaed8;
  line-height: 1.2;
}

.stat-box.highlight .stat-number {
  color: #f59e0b;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
}

/* 主内容区域 */
.main-area {
  display: flex;
  gap: 20px;
}

.work-section {
  flex: 1;
  min-width: 0;
}

/* 内容卡片 */
.content-card {
  background: white;
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.card-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.card-subtitle {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

.btn-add-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  color: #4b5563;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-item:hover:not(:disabled) {
  border-color: #7aaed8;
  color: #7aaed8;
}

.btn-add-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 18px;
  font-weight: 300;
}

/* 工作项 */
.work-items {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.work-item {
  position: relative;
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  overflow: visible;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.item-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 500;
  color: #374151;
}

.item-index {
  width: 24px;
  height: 24px;
  background: #7aaed8;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.item-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 项目选择器 */
.project-select {
  width: 140px;
}

.project-select :deep(.el-select__wrapper) {
  border-radius: 8px;
  font-size: 13px;
}

/* 表单组 */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 10px;
  font-weight: 500;
}

.form-label svg {
  width: 15px;
  height: 15px;
  color: #9ca3af;
}

/* 工作内容输入框样式 */
.form-group :deep(.el-textarea__inner) {
  border-radius: 10px;
  border-color: #e5e7eb;
  padding: 14px 16px;
  font-size: 14px;
  line-height: 1.6;
}

.form-group :deep(.el-textarea__inner):focus {
  border-color: #7aaed8;
}

.form-row {
  display: flex;
  gap: 24px;
}

/* 工时输入 */
.hours-group {
  flex: 1;
}

.hours-input-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hours-input {
  width: 100px;
}

.hours-quick-btns {
  display: flex;
  gap: 6px;
}

.quick-hour-btn {
  padding: 6px 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  color: #6b7280;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-hour-btn:hover:not(:disabled) {
  border-color: #7aaed8;
  color: #7aaed8;
}

.quick-hour-btn.active {
  background: #7aaed8;
  border-color: #7aaed8;
  color: white;
}

.quick-hour-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 进度滑块 */
.status-group {
  flex: 1;
}

.status-buttons {
  display: flex;
  gap: 8px;
}

.status-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(229, 231, 235, 0.6);
  border-radius: 8px;
  background: white;
  color: #9ca3af;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

/* 未开始图标：空心圆 */
.status-icon-circle {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid rgba(156, 163, 175, 0.4);
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.status-icon-circle.active {
  border-color: #7aaed8;
}

/* 进行中图标：半实心圆 */
.status-icon-half {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid rgba(156, 163, 175, 0.4);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  transition: all 0.15s ease;
}

.status-icon-half::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 50%;
  height: 100%;
  background: rgba(156, 163, 175, 0.4);
  transition: all 0.15s ease;
}

.status-icon-half.active {
  border-color: #f97316;
}

.status-icon-half.active::before {
  background: #f97316;
}

/* 已完成图标：实心圆+勾选 */
.status-icon-check {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: rgba(156, 163, 175, 0.4);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.status-icon-check svg {
  width: 8px;
  height: 8px;
  stroke: #9ca3af;
  transition: all 0.15s ease;
}

.status-icon-check.active {
  background: #7aaed8;
}

.status-icon-check.active svg {
  stroke: white;
}

/* hover 状态（未选中时） */
.status-btn:hover:not(:disabled):not(.active) {
  border-color: rgba(122, 174, 216, 0.3);
  color: #374151;
}

/* 所有选中态的共同样式：淡蓝背景 + 蓝边框 + 蓝文字 */
.status-btn.active {
  background: rgba(122, 174, 216, 0.1);
  border-color: rgba(122, 174, 216, 0.4);
  color: #7aaed8;
}

.status-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.progress-label-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.progress-label-left .percent-icon {
  width: 15px;
  height: 15px;
  color: #9ca3af;
  font-weight: 600;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-label-left .task-name {
  color: #7aaed8;
  font-weight: 600;
}

.progress-value {
  color: #10b981;
  font-weight: 600;
  font-size: 14px;
}

.progress-slider-wrapper {
  padding: 0 4px;
}

.progress-slider-wrapper :deep(.el-slider__runway) {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
}

.progress-slider-wrapper :deep(.el-slider__bar) {
  height: 6px;
  background: linear-gradient(90deg, #7aaed8, #5bc0de);
  border-radius: 3px;
}

.progress-slider-wrapper :deep(.el-slider__button) {
  width: 16px;
  height: 16px;
  border: 2px solid #7aaed8;
  background: white;
}

.progress-slider-wrapper :deep(.el-slider__button-wrapper) {
  top: -15px;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 8px;
  padding: 0 2px;
}

/* 删除按钮 - 卡片外部右上角 */
.btn-delete-item {
  position: absolute;
  top: -10px;
  right: -10px;
  background: white;
  border: 1px solid #e5e7eb;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn-delete-item:hover:not(:disabled) {
  color: #ef4444;
  background: #fef2f2;
  border-color: #fecaca;
}

.btn-delete-item:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-delete-item svg {
  width: 14px;
  height: 14px;
}

/* 备注区域 */
.remark-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}

/* 分割线 */
.card-divider {
  height: 1px;
  background: #f3f4f6;
  margin: 24px 0;
}

/* 操作按钮 */
.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn svg {
  width: 16px;
  height: 16px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #7aaed8;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5a9ac8;
}

.btn-secondary {
  background: white;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.btn-secondary:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.btn-danger {
  background: white;
  color: #ef4444;
  border: 1px solid #fecaca;
}

.btn-danger:hover:not(:disabled) {
  background: #fef2f2;
}

/* 锁定提示 */
.locked-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  color: #856404;
  font-size: 14px;
  margin-top: 16px;
}

.locked-notice svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* 本周概览 */
.week-overview {
  width: 220px;
  flex-shrink: 0;
}

.overview-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  position: sticky;
  top: 88px;
}

.overview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #374151;
  font-size: 14px;
  margin-bottom: 16px;
}

.overview-header svg {
  width: 18px;
  height: 18px;
  color: #7aaed8;
}

.week-days {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.day-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
}

.day-item:hover:not(.future) {
  background: #f0f7ff;
}

.day-name {
  font-size: 14px;
  color: #4b5563;
  font-weight: 500;
}

.day-status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 14px;
  font-weight: 600;
}

/* 脉动动画 - 发光呼吸效果 */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.5);
  }
  50% {
    transform: scale(1.2);
    box-shadow: 0 0 0 6px rgba(245, 158, 11, 0);
  }
}

/* 右侧状态符号颜色 */
.day-status-icon.submitted {
  color: #7aaed8;
}

.check-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: #e8f4fc;
  border-radius: 50%;
}

.check-circle svg {
  width: 14px;
  height: 14px;
}

.day-status-icon.editing {
  /* 使用父级的 flex 居中 */
}

/* 编辑中状态的橙色圆点 */
.editing-dot {
  width: 10px;
  height: 10px;
  background: #f59e0b;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.day-status-icon.empty {
  color: #c0c4cc;
}

.day-status-icon.future {
  color: #dcdfe6;
}

/* 未来日期 */
.day-item.future {
  cursor: not-allowed;
  opacity: 0.5;
}

/* 当前选中的日期 */
.day-item.selected {
  background: #e8f4fc;
  border-radius: 8px;
}

.day-item.selected .day-name {
  color: #374151;
  font-weight: 600;
}

/* 选中日期的状态图标保持默认样式 */

.overview-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #9ca3af;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.editing {
  background: #f59e0b;
}

.dot.empty {
  background: transparent;
  border: 1.5px solid #c0c4cc;
}

.legend-check-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  background: #e8f4fc;
  border-radius: 50%;
}

.legend-check-circle svg {
  width: 10px;
  height: 10px;
}

/* 任务选择器 */
.task-select {
  width: 180px;
}

.task-select :deep(.el-select__wrapper) {
  border-radius: 8px;
  font-size: 13px;
}

.task-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.task-option-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-option-progress {
  color: #7aaed8;
  font-size: 12px;
  font-weight: 500;
  margin-left: 12px;
}

/* 任务进度行 */
.task-progress-row {
  margin-top: 16px;
}

.task-progress-row .form-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 响应式 */
@media (max-width: 900px) {
  .main-area {
    flex-direction: column;
  }

  .week-overview {
    width: 100%;
    order: -1;
  }

  .overview-card {
    position: static;
  }

  .week-days {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .day-item {
    flex: 1;
    min-width: 80px;
    flex-direction: column;
    gap: 4px;
    padding: 10px 8px;
    text-align: center;
  }

  .overview-legend {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .header-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 20px;
  }

  .header-stats {
    width: 100%;
  }

  .stat-box {
    flex: 1;
  }

  .content-card {
    padding: 20px;
  }

  .card-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .form-row {
    flex-direction: column;
    gap: 16px;
  }

  .hours-input-row {
    flex-wrap: wrap;
  }

  .action-bar {
    flex-direction: column;
  }

  .action-bar .btn {
    width: 100%;
  }
}
</style>
