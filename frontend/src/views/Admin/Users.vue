<script setup>
import { ref, onMounted } from 'vue'
import request from '../../api/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingUser = ref(null)

const form = ref({
  username: '',
  password: '',
  real_name: '',
  department: '产品研发部',
  role: 'user'
})

const fetchUsers = async () => {
  loading.value = true
  try {
    users.value = await request.get('/admin/users/')
  } finally {
    loading.value = false
  }
}

onMounted(fetchUsers)

const openDialog = (user = null) => {
  editingUser.value = user
  if (user) {
    form.value = { ...user, password: '' }
  } else {
    form.value = {
      username: '',
      password: '',
      real_name: '',
      department: '产品研发部',
      role: 'user'
    }
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    if (editingUser.value) {
      await request.put(`/admin/users/${editingUser.value.id}`, {
        real_name: form.value.real_name,
        department: form.value.department,
        role: form.value.role,
        is_active: form.value.is_active
      })
      ElMessage.success('更新成功')
    } else {
      await request.post('/admin/users/', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (e) {
    // handled
  }
}

const handleDelete = async (user) => {
  await ElMessageBox.confirm(`确定删除用户 ${user.real_name} 吗？`, '确认删除')
  try {
    await request.delete(`/admin/users/${user.id}`)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (e) {
    // handled
  }
}

const handleResetPassword = async (user) => {
  await ElMessageBox.confirm(`确定重置 ${user.real_name} 的密码为 123456 吗？`, '确认重置')
  try {
    await request.put(`/admin/users/${user.id}/reset-password`)
    ElMessage.success('密码已重置为 123456')
  } catch (e) {
    // handled
  }
}
</script>

<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="header">
          <span>用户管理</span>
          <el-button type="primary" @click="openDialog()">添加用户</el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="department" label="部门" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : ''">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-button size="small" @click="handleResetPassword(row)">重置密码</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingUser ? '编辑用户' : '添加用户'"
      width="500"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" v-if="!editingUser">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" v-if="!editingUser">
          <el-input v-model="form.password" type="password" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" v-if="editingUser">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.users-page {
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
