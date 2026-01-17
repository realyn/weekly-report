<script setup>
import { ref, onMounted, computed } from 'vue'
import { useReportStore } from '../stores/report'
import { reportApi } from '../api/report'
import { ElMessage } from 'element-plus'

const reportStore = useReportStore()

// 整体文本输入
const thisWeekWork = ref('')
const nextWeekPlan = ref('')

// 截止时间信息
const deadlineInfo = ref(null)
const isLoading = ref(true)

// 解析预览
const parseResult = ref(null)
const isParsing = ref(false)

// 项目列表（用于下拉选择，包含子项）
const projectList = ref([])

// 项目选择弹窗状态
const showProjectModal = ref(false)
const projectModalTarget = ref(null) // { type: 'this_week', index: 0 }
const projectModalStep = ref(1) // 1: 选择项目, 2: 选择子项
const selectedProject = ref(null) // 当前选中的项目（用于显示子项）

// 新增项目弹窗
const showNewProjectDialog = ref(false)
const newProjectName = ref('')
const newProjectTarget = ref(null) // { type: 'this_week', index: 0 }
const newProjectType = ref('project') // 'project' 或 'sub_item'
const newProjectParent = ref(null) // 父项目名称（新增子分类时使用）

// ISO 周计算函数
const getISOWeekAndYear = (date) => {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  d.setDate(d.getDate() + 4 - (d.getDay() || 7))
  const isoYear = d.getFullYear()
  const yearStart = new Date(isoYear, 0, 1)
  const isoWeek = Math.ceil((((d - yearStart) / 86400000) + 1) / 7)
  return { isoYear, isoWeek }
}

// 获取ISO周的周一日期
const getMondayOfWeek = (isoYear, isoWeek) => {
  const jan4 = new Date(isoYear, 0, 4)
  const jan4Day = jan4.getDay() || 7
  const firstMonday = new Date(isoYear, 0, 4 - (jan4Day - 1))
  const targetMonday = new Date(firstMonday)
  targetMonday.setDate(firstMonday.getDate() + (isoWeek - 1) * 7)
  return targetMonday
}

// 获取周在月份中的序号
const getWeekInMonth = (isoYear, isoWeek) => {
  const monday = getMondayOfWeek(isoYear, isoWeek)
  const month = monday.getMonth()
  const year = monday.getFullYear()

  const firstDayOfMonth = new Date(year, month, 1)
  let firstMonday = new Date(firstDayOfMonth)
  const dayOfWeek = firstDayOfMonth.getDay()
  if (dayOfWeek !== 1) {
    const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek)
    firstMonday.setDate(firstDayOfMonth.getDate() + daysUntilMonday)
  }

  const weekDiff = Math.round((monday - firstMonday) / (7 * 24 * 60 * 60 * 1000))
  return weekDiff + 1
}

// 当前日期的ISO周信息
const now = new Date()
const { isoYear: currentYear, isoWeek: currentWeek } = getISOWeekAndYear(now)

// 周一日期
const weekMonday = computed(() => getMondayOfWeek(currentYear, currentWeek))

// 周日日期
const weekSunday = computed(() => {
  const sunday = new Date(weekMonday.value)
  sunday.setDate(sunday.getDate() + 6)
  return sunday
})

// 周所属的月份
const weekMonth = computed(() => weekMonday.value.getMonth() + 1)

// 周在月份中的序号
const weekInMonth = computed(() => getWeekInMonth(currentYear, currentWeek))

// 日期范围字符串
const dateRangeStr = computed(() => {
  const formatDate = (d) => `${d.getMonth() + 1}.${d.getDate()}`
  return `${formatDate(weekMonday.value)} - ${formatDate(weekSunday.value)}`
})

const isSubmitted = computed(() => reportStore.currentReport?.status === 'submitted')

// 是否可以编辑
const canEdit = computed(() => {
  if (!isSubmitted.value) return true
  return deadlineInfo.value && !deadlineInfo.value.is_expired
})

// 统计行数（非空行）
const countLines = (text) => {
  if (!text || !text.trim()) return 0
  return text.split('\n').filter(l => l.trim()).length
}

const taskCount = computed(() => countLines(thisWeekWork.value))
const planCount = computed(() => countLines(nextWeekPlan.value))

onMounted(async () => {
  const [_, deadlineRes, projects] = await Promise.all([
    reportStore.fetchCurrentReport(),
    reportApi.getDeadline(currentYear, currentWeek).catch(() => null),
    reportApi.getProjects().catch(() => [])
  ])

  if (reportStore.currentReport) {
    thisWeekWork.value = reportStore.currentReport.this_week_work || ''
    nextWeekPlan.value = reportStore.currentReport.next_week_plan || ''
  }

  if (deadlineRes?.data) {
    deadlineInfo.value = deadlineRes.data
  }

  // 加载项目列表
  projectList.value = projects || []

  isLoading.value = false
})

const handleSave = async (status = 'draft') => {
  try {
    const payload = {
      year: currentYear,
      week_num: currentWeek,
      this_week_work: thisWeekWork.value.trim(),
      next_week_plan: nextWeekPlan.value.trim(),
      status
    }

    // 如果有修正后的解析结果，一起发送
    if (parseResult.value) {
      if (parseResult.value.this_week_items?.length) {
        payload.this_week_items = parseResult.value.this_week_items
      }
      if (parseResult.value.next_week_items?.length) {
        payload.next_week_items = parseResult.value.next_week_items
      }
    }

    await reportStore.saveReport(payload)
    ElMessage.success(status === 'submitted' ? '提交成功' : '保存成功')

    // 清除解析结果
    parseResult.value = null

    const deadlineRes = await reportApi.getDeadline(currentYear, currentWeek).catch(() => null)
    if (deadlineRes?.data) {
      deadlineInfo.value = deadlineRes.data
    }
  } catch (e) {
    // error handled
  }
}

// 重置表单
const handleReset = () => {
  thisWeekWork.value = ''
  nextWeekPlan.value = ''
  parseResult.value = null
  ElMessage.info('已重置')
}

// 解析预览
const handleParsePreview = async () => {
  if (!thisWeekWork.value.trim() && !nextWeekPlan.value.trim()) {
    ElMessage.warning('请先输入内容')
    return
  }

  isParsing.value = true
  try {
    const res = await reportApi.parsePreview(thisWeekWork.value, nextWeekPlan.value)
    parseResult.value = res.data || res
    ElMessage.success('解析完成')
  } catch (e) {
    ElMessage.error('解析失败，请稍后重试')
  } finally {
    isParsing.value = false
  }
}

// 更新解析结果中的项目名称
const updateItemProject = (type, index, projectName) => {
  if (!parseResult.value) return
  const items = type === 'this_week' ? parseResult.value.this_week_items : parseResult.value.next_week_items
  if (items && items[index]) {
    items[index].project_name = projectName || null
  }
  closeDropdown()
}

// 打开项目选择弹窗
const openProjectModal = (type, index) => {
  projectModalTarget.value = { type, index }
  projectModalStep.value = 1
  selectedProject.value = null
  showProjectModal.value = true
}

// 关闭项目选择弹窗
const closeProjectModal = () => {
  showProjectModal.value = false
  projectModalTarget.value = null
  projectModalStep.value = 1
  selectedProject.value = null
}

// 选择项目（进入子项选择或直接确认）
const handleProjectClick = (proj) => {
  if (proj.sub_items?.length) {
    // 有子项，进入第二步
    selectedProject.value = proj
    projectModalStep.value = 2
  } else {
    // 无子项，直接选择
    confirmProjectSelection(proj.name)
  }
}

// 选择子项
const handleSubItemClick = (subItemName) => {
  if (selectedProject.value) {
    confirmProjectSelection(`${selectedProject.value.name}/${subItemName}`)
  }
}

// 返回项目列表
const backToProjectList = () => {
  projectModalStep.value = 1
  selectedProject.value = null
}

// 确认项目选择
const confirmProjectSelection = (projectName) => {
  if (projectModalTarget.value) {
    updateItemProject(
      projectModalTarget.value.type,
      projectModalTarget.value.index,
      projectName
    )
  }
  closeProjectModal()
}

// 清除项目分类
const clearProjectSelection = () => {
  if (projectModalTarget.value) {
    updateItemProject(
      projectModalTarget.value.type,
      projectModalTarget.value.index,
      null
    )
  }
  closeProjectModal()
}

// 从项目选择弹窗打开新增项目/子分类
const openNewProjectFromModal = (type = 'project') => {
  if (projectModalTarget.value) {
    newProjectTarget.value = { ...projectModalTarget.value }
  }
  newProjectName.value = ''
  newProjectType.value = type
  newProjectParent.value = type === 'sub_item' ? selectedProject.value?.name : null
  showProjectModal.value = false
  showNewProjectDialog.value = true
}

// 提交新增项目/子分类建议
const submitNewProject = async () => {
  if (!newProjectName.value.trim()) {
    ElMessage.warning(newProjectType.value === 'project' ? '请输入项目名称' : '请输入子分类名称')
    return
  }
  try {
    if (newProjectType.value === 'project') {
      // 新增一级项目
      await reportApi.suggestProject(newProjectName.value.trim())
      ElMessage.success('项目建议已提交，等待管理员审核')
      // 暂时使用该名称
      if (newProjectTarget.value) {
        updateItemProject(
          newProjectTarget.value.type,
          newProjectTarget.value.index,
          newProjectName.value.trim()
        )
      }
    } else {
      // 新增子分类
      await reportApi.suggestSubItem(newProjectParent.value, newProjectName.value.trim())
      ElMessage.success('子分类建议已提交，等待管理员审核')
      // 暂时使用 "父项目/子分类" 格式
      if (newProjectTarget.value && newProjectParent.value) {
        updateItemProject(
          newProjectTarget.value.type,
          newProjectTarget.value.index,
          `${newProjectParent.value}/${newProjectName.value.trim()}`
        )
      }
    }
    showNewProjectDialog.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败，请稍后重试')
  }
}

</script>

<template>
  <div class="page-container">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="page-header">
        <div class="header-main">
          <h1 class="page-title">
            <svg class="title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            填写周报
          </h1>
          <div class="week-info">
            <div class="week-label">{{ currentYear }}年{{ weekMonth }}月 · 第{{ weekInMonth }}周</div>
            <div class="week-date">{{ dateRangeStr }}</div>
          </div>
        </div>
        <div class="header-stats">
          <div class="mini-stat">
            <span class="mini-stat-number">{{ taskCount }}</span>
            <span class="mini-stat-label">本周任务</span>
          </div>
          <div class="mini-stat">
            <span class="mini-stat-number">{{ planCount }}</span>
            <span class="mini-stat-label">下周计划</span>
          </div>
        </div>
      </div>

      <!-- 本周工作内容 -->
      <div class="form-card">
        <div class="card-header">
          <div class="card-title">
            <svg class="title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
              <rect x="9" y="3" width="6" height="4" rx="1"/>
              <path d="M9 12h6M9 16h6"/>
            </svg>
            本周工作内容
          </div>
          <span class="input-hint">每行一条，系统会自动识别项目</span>
        </div>

        <textarea
          v-model="thisWeekWork"
          class="content-textarea"
          :placeholder="`推荐格式（按项目分组）：

【一省一报系统】
完成功能优化
修复登录问题

【大河云AI】
升级需求讨论
接口联调测试

也可以简单列出：
1. 完成xx功能开发
2. 参加xx会议`"
          :disabled="!canEdit"
          rows="8"
        ></textarea>
      </div>

      <!-- 下周工作计划 -->
      <div class="form-card">
        <div class="card-header">
          <div class="card-title">
            <svg class="title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2"/>
              <path d="M16 2v4M8 2v4M3 10h18"/>
            </svg>
            下周工作计划
          </div>
          <span class="input-hint">每行一条，系统会自动识别项目</span>
        </div>

        <textarea
          v-model="nextWeekPlan"
          class="content-textarea"
          :placeholder="`推荐格式（按项目分组）：

【清明上河图】
网站更新
内容维护

【通用】
编写接口文档
参加技术评审`"
          :disabled="!canEdit"
          rows="6"
        ></textarea>
      </div>

      <!-- 解析预览按钮 -->
      <div class="parse-action" v-if="canEdit">
        <button class="btn btn-parse" @click="handleParsePreview" :disabled="isParsing">
          <svg v-if="!isParsing" class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <span v-else class="loading-spinner"></span>
          {{ isParsing ? '解析中...' : '预览解析结果' }}
        </button>
        <span class="parse-hint">点击查看系统如何识别您的工作内容</span>
      </div>

      <!-- 解析结果预览 -->
      <div class="parse-preview" v-if="parseResult">
        <div class="preview-header">
          <div class="preview-title-area">
            <div class="preview-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 6L9 17l-5-5"/>
              </svg>
            </div>
            <div class="preview-title-text">
              <h3>解析结果预览</h3>
              <p>系统已智能识别并分类您的工作内容</p>
            </div>
          </div>
          <button class="btn-close" @click="parseResult = null">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="preview-section" v-if="parseResult.this_week_items?.length">
          <div class="section-label">本周工作 <span class="item-count">({{ parseResult.this_week_items.length }}条)</span></div>
          <div class="parsed-items">
            <div class="parsed-item" v-for="(item, index) in parseResult.this_week_items" :key="'tw-' + index">
              <span class="item-content">{{ item.content }}</span>
              <button
                class="project-tag"
                :class="{ 'no-project': !item.project_name }"
                @click="openProjectModal('this_week', index)"
              >
                {{ item.project_name || '未分类' }}
              </button>
            </div>
          </div>
        </div>

        <div class="preview-section" v-if="parseResult.next_week_items?.length">
          <div class="section-label">下周计划 <span class="item-count">({{ parseResult.next_week_items.length }}条)</span></div>
          <div class="parsed-items">
            <div class="parsed-item" v-for="(item, index) in parseResult.next_week_items" :key="'nw-' + index">
              <span class="item-content">{{ item.content }}</span>
              <button
                class="project-tag"
                :class="{ 'no-project': !item.project_name }"
                @click="openProjectModal('next_week', index)"
              >
                {{ item.project_name || '未分类' }}
              </button>
            </div>
          </div>
        </div>

        <div class="preview-empty" v-if="!parseResult.this_week_items?.length && !parseResult.next_week_items?.length">
          暂无可解析的内容
        </div>
      </div>

      <!-- 项目选择弹窗 -->
      <div class="dialog-overlay" v-if="showProjectModal" @click="closeProjectModal">
        <div class="dialog-content project-modal" @click.stop>
          <div class="dialog-header">
            <h3>
              <button v-if="projectModalStep === 2" class="btn-back" @click="backToProjectList">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M15 18l-6-6 6-6"/>
                </svg>
              </button>
              {{ projectModalStep === 1 ? '选择项目' : selectedProject?.name }}
            </h3>
            <button class="btn-close" @click="closeProjectModal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="dialog-body project-list-body">
            <p class="dialog-hint">{{ projectModalStep === 1 ? '请选择该工作项所属的项目分类' : '请选择子分类' }}</p>

            <!-- 第一步：项目列表 -->
            <div class="project-list" v-if="projectModalStep === 1">
              <div
                class="project-item"
                v-for="proj in projectList"
                :key="proj.name"
                @click="handleProjectClick(proj)"
              >
                <span class="project-name">{{ proj.name }}</span>
                <svg v-if="proj.sub_items?.length" class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18l6-6-6-6"/>
                </svg>
              </div>
              <div class="project-item add-new" @click="openNewProjectFromModal('project')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                <span>新增项目</span>
              </div>
            </div>

            <!-- 第二步：子项列表 -->
            <div class="project-list" v-if="projectModalStep === 2 && selectedProject">
              <div
                class="project-item"
                @click="confirmProjectSelection(selectedProject.name)"
              >
                <span class="project-name">{{ selectedProject.name }}（总体）</span>
              </div>
              <div
                class="project-item"
                v-for="subItem in selectedProject.sub_items"
                :key="subItem.name"
                @click="handleSubItemClick(subItem.name)"
              >
                <span class="project-name">{{ subItem.name }}</span>
              </div>
              <div class="project-item add-new" @click="openNewProjectFromModal('sub_item')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                <span>新增子分类</span>
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn btn-secondary" @click="clearProjectSelection">清除分类</button>
          </div>
        </div>
      </div>

      <!-- 新增项目/子分类弹窗 -->
      <div class="dialog-overlay" v-if="showNewProjectDialog" @click="showNewProjectDialog = false">
        <div class="dialog-content" @click.stop>
          <div class="dialog-header">
            <h3>{{ newProjectType === 'project' ? '新增项目' : `新增子分类` }}</h3>
            <button class="btn-close" @click="showNewProjectDialog = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="dialog-body">
            <p class="dialog-hint" v-if="newProjectType === 'project'">
              新增的项目将作为一级项目，提交后需等待管理员审核。
            </p>
            <p class="dialog-hint" v-else>
              为「{{ newProjectParent }}」新增子分类，提交后需等待管理员审核。
            </p>
            <input
              v-model="newProjectName"
              type="text"
              class="dialog-input"
              :placeholder="newProjectType === 'project' ? '请输入项目名称' : '请输入子分类名称'"
              @keyup.enter="submitNewProject"
            />
          </div>
          <div class="dialog-footer">
            <button class="btn btn-secondary" @click="showNewProjectDialog = false">取消</button>
            <button class="btn btn-primary" @click="submitNewProject">提交建议</button>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar" v-if="canEdit">
        <button class="btn btn-reset" @click="handleReset">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1 4v6h6M23 20v-6h-6"/>
            <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
          </svg>
          重置
        </button>
        <button v-if="!isSubmitted" class="btn btn-secondary" @click="handleSave('draft')">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
            <path d="M17 21v-8H7v8M7 3v5h8"/>
          </svg>
          保存草稿
        </button>
        <button class="btn btn-primary" @click="handleSave('submitted')">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
          </svg>
          {{ isSubmitted ? '更新周报' : '提交周报' }}
        </button>
      </div>

      <!-- 已提交状态提示 -->
      <div class="submitted-notice" :class="{ editable: canEdit && isSubmitted, expired: !canEdit && isSubmitted }" v-if="isSubmitted && !isLoading">
        <div class="notice-text">
          <strong>{{ canEdit ? '周报可修改' : '周报已锁定' }}</strong>
          <p v-if="deadlineInfo">
            {{ canEdit
              ? `截止时间: ${deadlineInfo.deadline_str}，${deadlineInfo.remaining}`
              : '已超过修改截止时间，如需修改请联系管理员'
            }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #f8fafc;
}

.page-content {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  padding: 24px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 24px;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #0f172a;
  letter-spacing: -0.025em;
  margin: 0;
  white-space: nowrap;
}

.week-info {
  padding-left: 24px;
  border-left: 2px solid #e2e8f0;
}

.week-label {
  font-size: 1.125rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 4px;
}

.week-date {
  font-size: 14px;
  color: #64748b;
}

.header-stats {
  display: flex;
  gap: 20px;
}

.mini-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.mini-stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: #7aaed8;
  line-height: 1;
}

.mini-stat:last-child .mini-stat-number {
  color: #f59e0b;
}

.mini-stat-label {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
}

/* 表单卡片 */
.form-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.card-title {
  font-size: 1rem;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.title-icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  color: #94a3b8;
}

.input-hint {
  font-size: 13px;
  color: #94a3b8;
}

/* 文本输入框 */
.content-textarea {
  width: 100%;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  transition: all 0.2s ease;
  background: #f8fafc;
  font-family: inherit;
}

.content-textarea:focus {
  outline: none;
  border-color: #7aaed8;
  background: white;
  box-shadow: 0 0 0 3px rgba(99, 176, 221, 0.15);
}

.content-textarea:disabled {
  background: #f1f5f9;
  color: #64748b;
  cursor: not-allowed;
}

.content-textarea::placeholder {
  color: #94a3b8;
}

/* 操作按钮 */
.action-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.btn-secondary {
  background: white;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.btn-secondary:hover {
  background: #f8fafc;
  color: #334155;
  border-color: #cbd5e1;
}

.btn-reset {
  background: white;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
}

.btn-reset:hover {
  background: #fef2f2;
  color: #ef4444;
  border-color: #fecaca;
}

.btn-primary {
  background: #7aaed8;
  color: white;
}

.btn-primary:hover {
  background: #4a9bc4;
}

/* 已提交提示 */
.submitted-notice {
  padding: 16px 20px;
  border-radius: 8px;
  margin-top: 24px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.notice-text strong {
  font-size: 14px;
  color: #64748b;
  display: block;
  margin-bottom: 4px;
  font-weight: 600;
}

.notice-text p {
  color: #94a3b8;
  font-size: 13px;
  margin: 0;
}

.submitted-notice.editable {
  background: #fffbeb;
  border-color: #fde68a;
}

.submitted-notice.editable .notice-text strong {
  color: #b45309;
}

.submitted-notice.editable .notice-text p {
  color: #d97706;
}

.submitted-notice.expired {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.submitted-notice.expired .notice-text strong {
  color: #64748b;
}

/* 解析预览按钮区域 */
.parse-action {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px 24px;
  background: #f0f9ff;
  border-radius: 12px;
  border: 1px dashed #7aaed8;
}

.btn-parse {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: white;
  color: #7aaed8;
  border: 1px solid #7aaed8;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-parse:hover:not(:disabled) {
  background: #7aaed8;
  color: white;
}

.btn-parse:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #7aaed8;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.parse-hint {
  color: #64748b;
  font-size: 13px;
}

/* 解析结果预览 */
.parse-preview {
  background: #f8f8f8;
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 16px;
  box-shadow: none;
  border: 1px solid #ebebeb;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.preview-title-area {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.preview-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.preview-icon svg {
  width: 18px;
  height: 18px;
  color: #444;
}

.preview-title-text h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.preview-title-text p {
  margin: 0;
  font-size: 13px;
  color: #888;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #666;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-close svg {
  width: 20px;
  height: 20px;
}

.btn-close:hover {
  background: #f0f0f0;
  color: #333;
}

.preview-section {
  margin-bottom: 20px;
}

.preview-section:last-child {
  margin-bottom: 0;
}

.section-label {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.section-label .item-count {
  font-weight: 400;
  color: #888;
}

.parsed-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.parsed-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  background: white;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s ease;
  min-height: 48px;
  box-sizing: border-box;
}

.parsed-item:hover {
  border-color: #e8e8e8;
}

.item-content {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  word-break: break-word;
  padding-top: 2px;
}

/* 项目标签 */
.project-tag {
  flex-shrink: 0;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 400;
  color: #333;
  background: #f8fafc;
  border: none;
  border-radius: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.project-tag:hover {
  background: #eef2f6;
}

.project-tag.no-project {
  background: #f8fafc;
  color: #fa541c;
}

/* 项目选择弹窗 */
.project-modal {
  width: 420px;
  max-width: 90vw;
  border-radius: 16px;
}

.project-modal .dialog-header {
  padding: 20px 24px 16px;
  border-bottom: none;
}

.project-modal .dialog-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.project-modal .btn-close {
  width: 32px;
  height: 32px;
}

.project-modal .btn-close svg {
  width: 18px;
  height: 18px;
}

.btn-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: #f5f5f5;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-back:hover {
  background: #e5e5e5;
}

.btn-back svg {
  width: 18px;
  height: 18px;
  color: #666;
}

.project-list-body {
  padding: 0 !important;
}

.project-list-body .dialog-hint {
  padding: 0 24px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #666;
}

.project-list {
  max-height: 360px;
  overflow-y: auto;
  padding: 0 8px;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 4px;
  font-size: 15px;
  color: #333;
  cursor: pointer;
  transition: background 0.15s ease;
  border-radius: 8px;
}

.project-item:hover {
  background: #f5f5f5;
}

.project-item .project-name {
  flex: 1;
}

.project-item .arrow-icon {
  width: 20px;
  height: 20px;
  color: #999;
  flex-shrink: 0;
}

.project-item.add-new {
  color: #1890ff;
  gap: 10px;
  justify-content: flex-start;
  margin-top: 8px;
  border-top: 1px solid #f0f0f0;
  border-radius: 0;
  padding-top: 16px;
}

.project-item.add-new svg {
  width: 18px;
  height: 18px;
}

.project-modal .dialog-footer {
  padding: 16px 24px 20px;
  border-top: none;
}

.preview-empty {
  text-align: center;
  color: #999;
  font-size: 14px;
  padding: 32px;
}

/* 新增项目弹窗 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  animation: fadeIn 0.2s ease;
}

.dialog-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.dialog-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.dialog-body {
  padding: 20px;
}

.dialog-hint {
  margin: 0 0 16px 0;
  font-size: 13px;
  color: #888;
  line-height: 1.5;
}

.dialog-input {
  width: 100%;
  padding: 12px 14px;
  font-size: 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  box-sizing: border-box;
}

.dialog-input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #eee;
}

/* 响应式 */
@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-main {
    width: 100%;
    justify-content: space-between;
  }

  .header-stats {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 20px 16px;
  }

  .header-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .page-title {
    font-size: 1.25rem;
  }

  .week-info {
    padding-left: 0;
    border-left: none;
    padding-top: 8px;
    border-top: 1px solid #e2e8f0;
    width: 100%;
  }

  .header-stats {
    gap: 12px;
  }

  .mini-stat {
    flex: 1;
    justify-content: center;
    padding: 12px;
  }

  .card-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }

  .action-bar {
    flex-direction: column;
  }

  .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
