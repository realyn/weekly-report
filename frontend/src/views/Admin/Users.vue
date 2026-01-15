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
    const data = await request.get('/admin/users/')
    // 管理员排第一，其他按 id 排序
    users.value = data.sort((a, b) => {
      if (a.role === 'admin' && b.role !== 'admin') return -1
      if (a.role !== 'admin' && b.role === 'admin') return 1
      return a.id - b.id
    })
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
  <div class="page-container">
    <div class="page-content">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">用户管理</h1>
        <button class="btn btn-primary" @click="openDialog()">添加用户</button>
      </div>

      <!-- 用户列表 -->
      <div class="card">

        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div class="table-container" v-else-if="users.length">
          <table class="member-table">
            <thead>
              <tr>
                <th style="width: 110px">姓名</th>
                <th>部门</th>
                <th style="width: 90px">角色</th>
                <th style="width: 70px">状态</th>
                <th style="width: 220px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id">
                <td>
                  <span class="user-name">{{ user.real_name }}</span>
                </td>
                <td>{{ user.department }}</td>
                <td>
                  <span class="role-badge" :class="user.role === 'admin' ? 'admin' : 'user'">
                    {{ user.role === 'admin' ? '管理员' : '普通用户' }}
                  </span>
                </td>
                <td>
                  <span class="status-badge" :class="user.is_active ? 'active' : 'inactive'">
                    {{ user.is_active ? '启用' : '禁用' }}
                  </span>
                </td>
                <td>
                  <div class="action-cell">
                    <button class="action-btn edit" @click="openDialog(user)">编辑</button>
                    <button class="action-btn reset" @click="handleResetPassword(user)">重置密码</button>
                    <button class="action-btn delete" @click="handleDelete(user)">删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="empty-state" v-else>
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-6l-2 3h-4l-2-3H2"/>
            <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>
          </svg>
          <p>暂无用户数据</p>
        </div>
      </div>
    </div>

    <!-- 用户编辑弹窗 -->
    <div class="modal-overlay" v-if="dialogVisible" @click.self="dialogVisible = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingUser ? '编辑用户' : '添加用户' }}</h3>
          <button class="modal-close" @click="dialogVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group" v-if="!editingUser">
            <label class="form-label">用户名</label>
            <input type="text" v-model="form.username" class="form-input" placeholder="请输入用户名" />
          </div>
          <div class="form-group" v-if="!editingUser">
            <label class="form-label">密码</label>
            <input type="password" v-model="form.password" class="form-input" placeholder="请输入密码" />
          </div>
          <div class="form-group">
            <label class="form-label">姓名</label>
            <input type="text" v-model="form.real_name" class="form-input" placeholder="请输入姓名" />
          </div>
          <div class="form-group">
            <label class="form-label">部门</label>
            <input type="text" v-model="form.department" class="form-input" placeholder="请输入部门" />
          </div>
          <div class="form-group">
            <label class="form-label">角色</label>
            <select v-model="form.role" class="form-select">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          <div class="form-group" v-if="editingUser">
            <label class="form-label">状态</label>
            <label class="switch">
              <input type="checkbox" v-model="form.is_active" />
              <span class="slider"></span>
              <span class="switch-label">{{ form.is_active ? '启用' : '禁用' }}</span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="dialogVisible = false">取消</button>
          <button class="btn btn-primary" @click="handleSubmit">确定</button>
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
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
  letter-spacing: -0.025em;
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #7aaed8;
  color: white;
}

.btn-primary:hover {
  background: #4a9bc4;
}

.btn-secondary {
  background: white;
  color: #475569;
  border: 1px solid #e2e8f0;
}

.btn-secondary:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

/* 卡片 */
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

/* 表格 */
.table-container {
  overflow-x: auto;
  border-radius: 8px;
}

.member-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.member-table th,
.member-table td {
  padding: 14px 16px;
  text-align: left;
}

.member-table th {
  background: transparent;
  color: #64748b;
  font-weight: 500;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.member-table td {
  border-bottom: 1px solid #f1f5f9;
  font-size: 14px;
  color: #334155;
}

.member-table tbody tr:hover {
  background: #f8fafc;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.role-badge {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.role-badge.admin {
  background: #e8f4fa;
  color: #7aaed8;
}

.role-badge.user {
  background: #f1f5f9;
  color: #64748b;
}

.status-badge {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.status-badge.active {
  background: #dcfce7;
  color: #16a34a;
}

.status-badge.inactive {
  background: #f1f5f9;
  color: #64748b;
}

.action-cell {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #f1f5f9;
  color: #64748b;
  white-space: nowrap;
}

.action-btn:hover {
  background: #e2e8f0;
  color: #475569;
}

.action-btn.edit {
  background: #e8f4fa;
  color: #4a9bc4;
}

.action-btn.edit:hover {
  background: #d1ebf7;
}

.action-btn.delete {
  color: #ef4444;
}

.action-btn.delete:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #64748b;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e2e8f0;
  border-top-color: #7aaed8;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px;
  color: #64748b;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #94a3b8;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
  animation: modalIn 0.2s ease;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 18px;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: #e2e8f0;
  color: #334155;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 8px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: white;
  color: #0f172a;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #7aaed8;
  box-shadow: 0 0 0 3px rgba(99, 176, 221, 0.15);
}

.form-select {
  cursor: pointer;
}

/* 开关 */
.switch {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.switch input {
  display: none;
}

.slider {
  width: 44px;
  height: 24px;
  background: #e2e8f0;
  border-radius: 12px;
  position: relative;
  transition: all 0.2s ease;
}

.slider::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  background: white;
  border-radius: 50%;
  top: 3px;
  left: 3px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.switch input:checked + .slider {
  background: #7aaed8;
}

.switch input:checked + .slider::after {
  left: 23px;
}

.switch-label {
  font-size: 14px;
  color: #64748b;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
  background: #f8fafc;
  border-radius: 0 0 12px 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }

  .page-header {
    padding: 16px;
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .page-title {
    font-size: 1.25rem;
    text-align: center;
  }

  .btn-primary {
    justify-content: center;
  }

  .action-cell {
    flex-direction: column;
    gap: 4px;
  }

  .action-btn {
    width: 100%;
    text-align: center;
  }
}
</style>
