<script setup>
import { ref, onMounted, computed } from 'vue'
import { useReportStore } from '../stores/report'
import { ElMessage } from 'element-plus'

const reportStore = useReportStore()

const form = ref({
  this_week_work: '',
  next_week_plan: '',
  status: 'draft'
})

const currentWeek = computed(() => {
  const now = new Date()
  const start = new Date(now.getFullYear(), 0, 1)
  const days = Math.floor((now - start) / (24 * 60 * 60 * 1000))
  return Math.ceil((days + start.getDay() + 1) / 7)
})

const currentYear = new Date().getFullYear()

onMounted(async () => {
  await reportStore.fetchCurrentReport()
  if (reportStore.currentReport) {
    form.value = {
      this_week_work: reportStore.currentReport.this_week_work || '',
      next_week_plan: reportStore.currentReport.next_week_plan || '',
      status: reportStore.currentReport.status
    }
  }
})

const handleSave = async (status = 'draft') => {
  try {
    await reportStore.saveReport({
      year: currentYear,
      week_num: currentWeek.value,
      this_week_work: form.value.this_week_work,
      next_week_plan: form.value.next_week_plan,
      status
    })
    ElMessage.success(status === 'submitted' ? '提交成功' : '保存成功')
  } catch (e) {
    // error handled
  }
}
</script>

<template>
  <div class="report-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ currentYear }}年 第{{ currentWeek }}周 工作周报</span>
          <el-tag v-if="reportStore.currentReport?.status === 'submitted'" type="success">已提交</el-tag>
          <el-tag v-else type="info">草稿</el-tag>
        </div>
      </template>

      <el-form label-position="top">
        <el-form-item label="本周工作内容">
          <el-input
            v-model="form.this_week_work"
            type="textarea"
            :rows="10"
            placeholder="请输入本周完成的工作内容，每项工作一行&#10;例如：&#10;1. 一省一报系统功能完善&#10;2. 智慧教育红干院运维&#10;3. 大语言模型推进"
            :disabled="reportStore.currentReport?.status === 'submitted'"
          />
        </el-form-item>

        <el-form-item label="下周工作计划">
          <el-input
            v-model="form.next_week_plan"
            type="textarea"
            :rows="8"
            placeholder="请输入下周的工作计划"
            :disabled="reportStore.currentReport?.status === 'submitted'"
          />
        </el-form-item>

        <el-form-item v-if="reportStore.currentReport?.status !== 'submitted'">
          <el-button @click="handleSave('draft')">保存草稿</el-button>
          <el-button type="primary" @click="handleSave('submitted')">提交周报</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.report-page {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
