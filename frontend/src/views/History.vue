<script setup>
import { ref, onMounted } from 'vue'
import { reportApi } from '../api/report'

const currentYear = new Date().getFullYear()
const year = ref(currentYear)
const reports = ref([])
const loading = ref(false)

const fetchReports = async () => {
  loading.value = true
  try {
    reports.value = await reportApi.getList(year.value)
  } catch (e) {
    // error handled
  } finally {
    loading.value = false
  }
}

onMounted(fetchReports)

const getStatusType = (status) => status === 'submitted' ? 'success' : 'info'
const getStatusText = (status) => status === 'submitted' ? '已提交' : '草稿'
</script>

<template>
  <div class="history-page">
    <el-card>
      <template #header>
        <div class="header">
          <span>我的历史周报</span>
          <div>
            <el-input-number v-model="year" :min="2020" :max="2030" @change="fetchReports" />
            <span style="margin-left: 8px">年</span>
          </div>
        </div>
      </template>

      <el-table :data="reports" v-loading="loading" stripe>
        <el-table-column label="周数" width="100">
          <template #default="{ row }">第{{ row.week_num }}周</template>
        </el-table-column>
        <el-table-column prop="this_week_work" label="本周工作" show-overflow-tooltip />
        <el-table-column prop="next_week_plan" label="下周计划" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ new Date(row.updated_at).toLocaleString() }}</template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && reports.length === 0" description="暂无历史周报" />
    </el-card>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
