<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    default: null
  },
  projects: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['save', 'cancel'])

// 表单数据
const form = ref({
  title: '',
  description: '',
  project_name: null,
  priority: 0,
  start_date: null,
  due_date: null
})

// 监听 task 变化，初始化表单
watch(() => props.task, (newTask) => {
  if (newTask) {
    form.value = {
      title: newTask.title || '',
      description: newTask.description || '',
      project_name: newTask.project_name || null,
      priority: newTask.priority ?? 0,
      start_date: newTask.start_date || null,
      due_date: newTask.due_date || null
    }
  } else {
    form.value = {
      title: '',
      description: '',
      project_name: null,
      priority: 0,
      start_date: null,
      due_date: null
    }
  }
}, { immediate: true })

// 是否编辑模式
const isEditMode = computed(() => !!props.task?.id)

// 优先级选项
const priorityOptions = [
  { value: 0, label: '普通', color: '#909399' },
  { value: 1, label: '低', color: '#67c23a' },
  { value: 2, label: '中', color: '#e6a23c' },
  { value: 3, label: '高', color: '#f56c6c' }
]

// 活跃项目
const activeProjects = computed(() => {
  return props.projects.filter(p => p.is_active)
})

// 不活跃项目
const inactiveProjects = computed(() => {
  return props.projects.filter(p => !p.is_active)
})

// 提交表单
const handleSubmit = () => {
  if (!form.value.title?.trim()) {
    return
  }
  emit('save', { ...form.value })
}

// 取消
const handleCancel = () => {
  emit('cancel')
}
</script>

<template>
  <div class="task-form">
    <div class="form-group">
      <label class="form-label required">任务标题</label>
      <el-input
        v-model="form.title"
        placeholder="请输入任务标题"
        maxlength="200"
        show-word-limit
      />
    </div>

    <div class="form-group">
      <label class="form-label">任务描述</label>
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="3"
        placeholder="请输入任务描述（可选）"
        maxlength="2000"
      />
    </div>

    <div class="form-row">
      <div class="form-group flex-1">
        <label class="form-label">关联项目</label>
        <el-select
          v-model="form.project_name"
          placeholder="选择项目"
          filterable
          clearable
          style="width: 100%"
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
      </div>

      <div class="form-group flex-1">
        <label class="form-label">优先级</label>
        <el-select v-model="form.priority" style="width: 100%">
          <el-option
            v-for="opt in priorityOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          >
            <span :style="{ color: opt.color }">{{ opt.label }}</span>
          </el-option>
        </el-select>
      </div>
    </div>

    <div class="form-row">
      <div class="form-group flex-1">
        <label class="form-label">开始日期</label>
        <el-date-picker
          v-model="form.start_date"
          type="date"
          placeholder="选择开始日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </div>

      <div class="form-group flex-1">
        <label class="form-label">截止日期</label>
        <el-date-picker
          v-model="form.due_date"
          type="date"
          placeholder="选择截止日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </div>
    </div>

    <div class="form-actions">
      <button type="button" class="btn btn-secondary" @click="handleCancel">取消</button>
      <button
        type="button"
        class="btn btn-primary"
        @click="handleSubmit"
        :disabled="!form.title?.trim()"
      >
        {{ isEditMode ? '保存修改' : '创建任务' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.task-form {
  padding: 8px 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-label.required::after {
  content: ' *';
  color: #f56c6c;
}

.form-row {
  display: flex;
  gap: 16px;
}

.flex-1 {
  flex: 1;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
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

.btn-secondary:hover {
  background: #f9fafb;
}

/* 输入框样式 */
:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 8px;
}

:deep(.el-input__wrapper):focus-within,
:deep(.el-textarea__inner):focus {
  box-shadow: 0 0 0 1px #7aaed8;
}
</style>
