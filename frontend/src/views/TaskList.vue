<script setup>
import { ref, onMounted, computed } from 'vue'
import { taskApi } from '../api/task'
import { reportApi } from '../api/report'
import { ElMessage, ElMessageBox } from 'element-plus'
import TaskForm from '../components/TaskForm.vue'

// 任务列表
const tasks = ref([])
const isLoading = ref(true)

// 筛选
const statusFilter = ref('')
const projectFilter = ref('')
const includeCompleted = ref(false)

// 项目列表
const projectList = ref([])

// 弹窗
const formDialogVisible = ref(false)
const editingTask = ref(null)
const detailDialogVisible = ref(false)
const taskDetail = ref(null)

// 状态配置
const statusConfig = {
  pending: { label: '待开始', color: '#909399', bgColor: '#f4f4f5' },
  in_progress: { label: '进行中', color: '#e6a23c', bgColor: '#fdf6ec' },
  completed: { label: '已完成', color: '#67c23a', bgColor: '#f0f9eb' },
  cancelled: { label: '已取消', color: '#909399', bgColor: '#f4f4f5' }
}

// 优先级配置
const priorityConfig = {
  0: { label: '普通', color: '#909399' },
  1: { label: '低', color: '#67c23a' },
  2: { label: '中', color: '#e6a23c' },
  3: { label: '高', color: '#f56c6c' }
}

// 加载任务列表
const loadTasks = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (projectFilter.value) params.project_name = projectFilter.value
    params.include_completed = includeCompleted.value

    tasks.value = await taskApi.getList(params)
  } catch (e) {
    ElMessage.error('加载任务失败')
  } finally {
    isLoading.value = false
  }
}

// 加载项目列表
const loadProjects = async () => {
  try {
    projectList.value = await reportApi.getProjects()
  } catch (e) {
    console.error('加载项目列表失败')
  }
}

onMounted(async () => {
  await Promise.all([loadTasks(), loadProjects()])
})

// 打开新建任务弹窗
const openCreateDialog = () => {
  editingTask.value = null
  formDialogVisible.value = true
}

// 打开编辑任务弹窗
const openEditDialog = (task) => {
  editingTask.value = { ...task }
  formDialogVisible.value = true
}

// 保存任务
const handleSaveTask = async (taskData) => {
  try {
    if (editingTask.value?.id) {
      await taskApi.update(editingTask.value.id, taskData)
      ElMessage.success('任务已更新')
    } else {
      await taskApi.create(taskData)
      ElMessage.success('任务已创建')
    }
    formDialogVisible.value = false
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

// 查看任务详情
const viewTaskDetail = async (task) => {
  try {
    taskDetail.value = await taskApi.getById(task.id)
    detailDialogVisible.value = true
  } catch (e) {
    ElMessage.error('加载任务详情失败')
  }
}

// 删除任务
const handleDelete = async (task) => {
  try {
    await ElMessageBox.confirm(`确定要删除任务「${task.title}」吗？`, '确认删除', {
      type: 'warning'
    })
    await taskApi.delete(task.id)
    ElMessage.success('任务已删除')
    await loadTasks()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

// 快速更新状态
const quickUpdateStatus = async (task, newStatus) => {
  try {
    await taskApi.update(task.id, { status: newStatus })
    ElMessage.success('状态已更新')
    await loadTasks()
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 统计数据
const stats = computed(() => {
  const all = tasks.value
  return {
    total: all.length,
    pending: all.filter(t => t.status === 'pending').length,
    inProgress: all.filter(t => t.status === 'in_progress').length,
    completed: all.filter(t => t.status === 'completed').length
  }
})
</script>

<template>
  <div class="page-container">
    <div class="page-content" v-loading="isLoading">
      <!-- 页面头部 -->
      <div class="header-card">
        <div class="header-left">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4"/>
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
            </svg>
          </div>
          <div class="header-info">
            <h1 class="header-title">任务管理</h1>
            <p class="header-subtitle">创建和追踪你的工作任务</p>
          </div>
        </div>
        <button class="btn btn-primary" @click="openCreateDialog">
          <span>+ 新建任务</span>
        </button>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <span class="stat-number">{{ stats.total }}</span>
          <span class="stat-label">全部任务</span>
        </div>
        <div class="stat-card pending">
          <span class="stat-number">{{ stats.pending }}</span>
          <span class="stat-label">待开始</span>
        </div>
        <div class="stat-card in-progress">
          <span class="stat-number">{{ stats.inProgress }}</span>
          <span class="stat-label">进行中</span>
        </div>
        <div class="stat-card completed">
          <span class="stat-number">{{ stats.completed }}</span>
          <span class="stat-label">已完成</span>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="loadTasks">
          <el-option label="待开始" value="pending" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-select v-model="projectFilter" placeholder="项目筛选" clearable filterable @change="loadTasks">
          <el-option
            v-for="p in projectList"
            :key="p.name"
            :label="p.name"
            :value="p.name"
          />
        </el-select>
        <el-checkbox v-model="includeCompleted" @change="loadTasks">显示已完成</el-checkbox>
      </div>

      <!-- 任务列表 -->
      <div class="task-list">
        <div v-if="tasks.length === 0" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="1"/>
          </svg>
          <p>暂无任务</p>
          <button class="btn btn-primary btn-sm" @click="openCreateDialog">创建第一个任务</button>
        </div>

        <div
          v-for="task in tasks"
          :key="task.id"
          class="task-card"
          :class="task.status"
        >
          <div class="task-main" @click="viewTaskDetail(task)">
            <div class="task-header">
              <span class="task-title">{{ task.title }}</span>
              <div class="task-badges">
                <span
                  class="badge priority"
                  :style="{ color: priorityConfig[task.priority].color }"
                  v-if="task.priority > 0"
                >
                  {{ priorityConfig[task.priority].label }}
                </span>
                <span
                  class="badge status"
                  :style="{
                    color: statusConfig[task.status].color,
                    background: statusConfig[task.status].bgColor
                  }"
                >
                  {{ statusConfig[task.status].label }}
                </span>
              </div>
            </div>
            <div class="task-meta">
              <span v-if="task.project_name" class="meta-item project">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
                </svg>
                {{ task.project_name }}
              </span>
              <span v-if="task.due_date" class="meta-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                  <line x1="16" y1="2" x2="16" y2="6"/>
                  <line x1="8" y1="2" x2="8" y2="6"/>
                  <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                截止: {{ formatDate(task.due_date) }}
              </span>
            </div>
            <div class="task-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: task.progress + '%' }"></div>
              </div>
              <span class="progress-text">{{ task.progress }}%</span>
            </div>
          </div>
          <div class="task-actions">
            <el-dropdown trigger="click" @command="(cmd) => quickUpdateStatus(task, cmd)">
              <button class="btn-icon-action">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="1"/>
                  <circle cx="19" cy="12" r="1"/>
                  <circle cx="5" cy="12" r="1"/>
                </svg>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="pending">设为待开始</el-dropdown-item>
                  <el-dropdown-item command="in_progress">设为进行中</el-dropdown-item>
                  <el-dropdown-item command="completed">设为已完成</el-dropdown-item>
                  <el-dropdown-item divided @click="openEditDialog(task)">编辑</el-dropdown-item>
                  <el-dropdown-item @click="handleDelete(task)" style="color: #f56c6c">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>

      <!-- 新建/编辑任务弹窗 -->
      <el-dialog
        v-model="formDialogVisible"
        :title="editingTask?.id ? '编辑任务' : '新建任务'"
        width="500px"
        :close-on-click-modal="false"
      >
        <TaskForm
          :task="editingTask"
          :projects="projectList"
          @save="handleSaveTask"
          @cancel="formDialogVisible = false"
        />
      </el-dialog>

      <!-- 任务详情弹窗 -->
      <el-dialog
        v-model="detailDialogVisible"
        title="任务详情"
        width="600px"
      >
        <div v-if="taskDetail" class="task-detail">
          <div class="detail-header">
            <h3>{{ taskDetail.title }}</h3>
            <span
              class="badge status"
              :style="{
                color: statusConfig[taskDetail.status].color,
                background: statusConfig[taskDetail.status].bgColor
              }"
            >
              {{ statusConfig[taskDetail.status].label }}
            </span>
          </div>

          <div class="detail-info">
            <div class="info-row" v-if="taskDetail.description">
              <label>描述</label>
              <p>{{ taskDetail.description }}</p>
            </div>
            <div class="info-row">
              <label>项目</label>
              <span>{{ taskDetail.project_name || '-' }}</span>
            </div>
            <div class="info-row">
              <label>进度</label>
              <div class="progress-display">
                <div class="progress-bar large">
                  <div class="progress-fill" :style="{ width: taskDetail.progress + '%' }"></div>
                </div>
                <span>{{ taskDetail.progress }}%</span>
              </div>
            </div>
            <div class="info-row">
              <label>截止日期</label>
              <span>{{ formatDate(taskDetail.due_date) }}</span>
            </div>
            <div class="info-row">
              <label>创建人</label>
              <span>{{ taskDetail.creator_name }}</span>
            </div>
            <div class="info-row" v-if="taskDetail.assignee_name">
              <label>负责人</label>
              <span>{{ taskDetail.assignee_name }}</span>
            </div>
          </div>

          <!-- 进度日志 -->
          <div class="progress-logs" v-if="taskDetail.progress_logs?.length > 0">
            <h4>进度记录</h4>
            <div class="log-timeline">
              <div
                v-for="log in taskDetail.progress_logs"
                :key="log.id"
                class="log-item"
              >
                <div class="log-date">{{ formatDate(log.date) }}</div>
                <div class="log-content">
                  <div class="log-progress">
                    {{ log.progress_before }}% → {{ log.progress_after }}%
                  </div>
                  <div class="log-text" v-if="log.content">{{ log.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <button class="btn btn-secondary" @click="detailDialogVisible = false">关闭</button>
          <button class="btn btn-primary" @click="openEditDialog(taskDetail); detailDialogVisible = false">编辑</button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #f5f7fa;
}

.page-content {
  max-width: 900px;
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

.header-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.header-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 4px 0 0;
}

/* 统计卡片 */
.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  background: white;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stat-number {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #374151;
}

.stat-label {
  font-size: 12px;
  color: #9ca3af;
}

.stat-card.pending .stat-number { color: #909399; }
.stat-card.in-progress .stat-number { color: #e6a23c; }
.stat-card.completed .stat-number { color: #67c23a; }

/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 16px 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.filter-bar .el-select {
  width: 160px;
}

/* 任务列表 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  background: white;
  border-radius: 16px;
  padding: 60px 20px;
  text-align: center;
  color: #9ca3af;
}

.empty-state svg {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #d1d5db;
}

.empty-state p {
  margin: 0 0 16px;
}

/* 任务卡片 */
.task-card {
  background: white;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.task-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.task-card.pending { border-left-color: #909399; }
.task-card.in_progress { border-left-color: #e6a23c; }
.task-card.completed { border-left-color: #67c23a; }
.task-card.cancelled { border-left-color: #909399; opacity: 0.6; }

.task-main {
  flex: 1;
  cursor: pointer;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-title {
  font-weight: 600;
  color: #374151;
}

.task-badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge.priority {
  background: transparent;
}

.task-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #6b7280;
}

.meta-item svg {
  width: 14px;
  height: 14px;
}

.meta-item.project {
  color: #7aaed8;
}

.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar.large {
  height: 8px;
  border-radius: 4px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7aaed8, #5bc0de);
  border-radius: 2px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: #9ca3af;
  min-width: 36px;
}

.task-actions {
  flex-shrink: 0;
}

.btn-icon-action {
  background: transparent;
  border: none;
  padding: 8px;
  cursor: pointer;
  color: #9ca3af;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-icon-action:hover {
  background: #f3f4f6;
  color: #374151;
}

.btn-icon-action svg {
  width: 20px;
  height: 20px;
}

/* 任务详情 */
.task-detail {
  padding: 0 8px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.detail-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #374151;
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.info-row label {
  width: 80px;
  font-size: 13px;
  color: #9ca3af;
  flex-shrink: 0;
}

.info-row span,
.info-row p {
  flex: 1;
  font-size: 14px;
  color: #374151;
  margin: 0;
}

.progress-display {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.progress-display .progress-bar {
  flex: 1;
}

/* 进度日志 */
.progress-logs {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}

.progress-logs h4 {
  margin: 0 0 16px;
  font-size: 14px;
  color: #374151;
}

.log-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-item {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: #fafbfc;
  border-radius: 8px;
}

.log-date {
  font-size: 13px;
  color: #9ca3af;
  min-width: 80px;
}

.log-content {
  flex: 1;
}

.log-progress {
  font-size: 14px;
  color: #7aaed8;
  font-weight: 500;
}

.log-text {
  font-size: 13px;
  color: #6b7280;
  margin-top: 4px;
}

/* 按钮 */
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

.btn-sm {
  padding: 8px 16px;
  font-size: 13px;
}

.btn-primary {
  background: #7aaed8;
  color: white;
}

.btn-primary:hover {
  background: #5a9ac8;
}

.btn-secondary {
  background: white;
  color: #6b7280;
  border: 1px solid #e5e7eb;
}

.btn-secondary:hover {
  background: #f9fafb;
}

/* 响应式 */
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

  .stats-row {
    flex-wrap: wrap;
  }

  .stat-card {
    min-width: calc(50% - 6px);
  }

  .filter-bar {
    flex-wrap: wrap;
  }

  .filter-bar .el-select {
    width: 100%;
  }
}
</style>
