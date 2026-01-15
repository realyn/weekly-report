<script setup>
import { ref, onMounted, computed } from 'vue'
import { useReportStore } from '../stores/report'
import { reportApi } from '../api/report'
import { ElMessage } from 'element-plus'

const reportStore = useReportStore()

// 本周工作条目列表
const thisWeekItems = ref([{ content: '' }])
// 下周计划条目列表
const nextWeekItems = ref([{ content: '' }])

// 截止时间信息
const deadlineInfo = ref(null)

// ISO 周计算函数（与Chart.vue和后端保持一致）
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

  // 找到该月第一个周一
  const firstDayOfMonth = new Date(year, month, 1)
  let firstMonday = new Date(firstDayOfMonth)
  const dayOfWeek = firstDayOfMonth.getDay()
  if (dayOfWeek !== 1) {
    const daysUntilMonday = dayOfWeek === 0 ? 1 : (8 - dayOfWeek)
    firstMonday.setDate(firstDayOfMonth.getDate() + daysUntilMonday)
  }

  // 计算当前周是该月第几周
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

// 周所属的月份（以周一所在月份为准）
const weekMonth = computed(() => weekMonday.value.getMonth() + 1)

// 周在月份中的序号
const weekInMonth = computed(() => getWeekInMonth(currentYear, currentWeek))

// 日期范围字符串
const dateRangeStr = computed(() => {
  const formatDate = (d) => `${d.getMonth() + 1}.${d.getDate()}`
  return `${formatDate(weekMonday.value)} - ${formatDate(weekSunday.value)}`
})

const isSubmitted = computed(() => reportStore.currentReport?.status === 'submitted')

// 是否可以编辑（未提交 或 已提交但未过截止时间）
const canEdit = computed(() => {
  if (!isSubmitted.value) return true
  return deadlineInfo.value && !deadlineInfo.value.is_expired
})

// 将字符串转换为条目数组
const parseToItems = (text) => {
  if (!text || !text.trim()) return [{ content: '' }]
  const lines = text.split('\n').filter(l => l.trim())
  if (lines.length === 0) return [{ content: '' }]
  return lines.map(line => {
    // 去除开头的序号（如 "1. " 或 "1、" 或 "1，"）
    const cleaned = line.replace(/^\d+[.、，,]\s*/, '').trim()
    return { content: cleaned }
  })
}

// 将条目数组转换为带序号的字符串
const itemsToString = (items) => {
  return items
    .filter(item => item.content.trim())
    .map((item, index) => `${index + 1}. ${item.content.trim()}`)
    .join('\n')
}

onMounted(async () => {
  // 并行获取周报和截止时间
  const [_, deadlineRes] = await Promise.all([
    reportStore.fetchCurrentReport(),
    reportApi.getDeadline(currentYear, currentWeek).catch(() => null)
  ])

  if (reportStore.currentReport) {
    thisWeekItems.value = parseToItems(reportStore.currentReport.this_week_work)
    nextWeekItems.value = parseToItems(reportStore.currentReport.next_week_plan)
  }

  if (deadlineRes?.data) {
    deadlineInfo.value = deadlineRes.data
  }
})

const handleSave = async (status = 'draft') => {
  try {
    await reportStore.saveReport({
      year: currentYear,
      week_num: currentWeek,
      this_week_work: itemsToString(thisWeekItems.value),
      next_week_plan: itemsToString(nextWeekItems.value),
      status
    })
    ElMessage.success(status === 'submitted' ? '提交成功' : '保存成功')

    // 刷新截止时间信息
    const deadlineRes = await reportApi.getDeadline(currentYear, currentWeek).catch(() => null)
    if (deadlineRes?.data) {
      deadlineInfo.value = deadlineRes.data
    }
  } catch (e) {
    // error handled
  }
}

// 添加条目
const addItem = (list) => {
  list.push({ content: '' })
}

// 删除条目
const removeItem = (list, index) => {
  if (list.length > 1) {
    list.splice(index, 1)
  } else {
    list[0].content = ''
  }
}

// 计算有效任务数
const taskCount = computed(() => {
  return thisWeekItems.value.filter(item => item.content.trim()).length
})

const planCount = computed(() => {
  return nextWeekItems.value.filter(item => item.content.trim()).length
})

// 重置表单
const handleReset = () => {
  thisWeekItems.value = [{ content: '' }]
  nextWeekItems.value = [{ content: '' }]
  ElMessage.info('已重置')
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
          <button
            v-if="canEdit"
            class="add-btn"
            @click="addItem(thisWeekItems)"
          >
            <span>+</span> 添加条目
          </button>
        </div>

        <div class="items-list">
          <div
            v-for="(item, index) in thisWeekItems"
            :key="'this-' + index"
            class="item-row"
          >
            <span class="item-number">{{ index + 1 }}</span>
            <input
              v-model="item.content"
              type="text"
              class="item-input"
              :placeholder="index === 0 ? '例如：一省一报系统功能完善' : '输入工作内容...'"
              :disabled="!canEdit"
            />
            <button
              v-if="canEdit && thisWeekItems.length > 1"
              class="remove-btn"
              @click="removeItem(thisWeekItems, index)"
            >
              ×
            </button>
          </div>
        </div>
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
          <button
            v-if="canEdit"
            class="add-btn"
            @click="addItem(nextWeekItems)"
          >
            <span>+</span> 添加条目
          </button>
        </div>

        <div class="items-list">
          <div
            v-for="(item, index) in nextWeekItems"
            :key="'next-' + index"
            class="item-row"
          >
            <span class="item-number">{{ index + 1 }}</span>
            <input
              v-model="item.content"
              type="text"
              class="item-input"
              :placeholder="index === 0 ? '例如：完成系统测试' : '输入计划内容...'"
              :disabled="!canEdit"
            />
            <button
              v-if="canEdit && nextWeekItems.length > 1"
              class="remove-btn"
              @click="removeItem(nextWeekItems, index)"
            >
              ×
            </button>
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
      <div class="submitted-notice" :class="{ editable: canEdit && isSubmitted, expired: !canEdit && isSubmitted }" v-if="isSubmitted">
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
/* v0.app 风格 */
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
  margin-bottom: 20px;
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

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-btn:hover {
  border-color: #7aaed8;
  color: #7aaed8;
  background: #e8f4fa;
}

.add-btn span {
  font-size: 16px;
  font-weight: 600;
}

/* 条目列表 */
.items-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.item-number {
  min-width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  color: #64748b;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

.item-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #f8fafc;
}

.item-input:focus {
  outline: none;
  border-color: #7aaed8;
  background: white;
  box-shadow: 0 0 0 3px rgba(99, 176, 221, 0.15);
}

.item-input:disabled {
  background: #f1f5f9;
  color: #64748b;
  cursor: not-allowed;
}

.item-input::placeholder {
  color: #94a3b8;
}

.remove-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: #fef2f2;
  color: #ef4444;
  font-size: 18px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.remove-btn:hover {
  background: #fee2e2;
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

/* 可编辑状态 */
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

/* 已过期状态 */
.submitted-notice.expired {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.submitted-notice.expired .notice-text strong {
  color: #64748b;
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
    gap: 12px;
    align-items: flex-start;
  }

  .add-btn {
    width: 100%;
    justify-content: center;
  }

  .item-row {
    flex-wrap: wrap;
  }

  .item-input {
    width: calc(100% - 80px);
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
