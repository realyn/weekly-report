<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { authApi } from '../api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const loading = ref(false)
const errorMsg = ref('')

// 密码验证规则
const passwordRules = [
  { check: (p) => p.length >= 8, text: '至少8位字符' },
  { check: (p) => /[A-Za-z]/.test(p), text: '包含字母' },
  { check: (p) => /\d/.test(p), text: '包含数字' }
]

// 检查各规则是否满足
const ruleStatus = computed(() => {
  const pwd = form.value.newPassword
  return passwordRules.map(rule => ({
    text: rule.text,
    passed: pwd ? rule.check(pwd) : null
  }))
})

// 验证密码
const validatePassword = (password) => {
  for (const rule of passwordRules) {
    if (!rule.check(password)) {
      return `密码需${rule.text}`
    }
  }
  return null
}

const handleSubmit = async () => {
  errorMsg.value = ''

  if (!form.value.oldPassword || !form.value.newPassword || !form.value.confirmPassword) {
    errorMsg.value = '请填写所有字段'
    return
  }

  const pwdError = validatePassword(form.value.newPassword)
  if (pwdError) {
    errorMsg.value = pwdError
    return
  }

  if (form.value.newPassword !== form.value.confirmPassword) {
    errorMsg.value = '两次输入的新密码不一致'
    return
  }

  loading.value = true
  try {
    await authApi.changePassword(form.value.oldPassword, form.value.newPassword)
    userStore.clearMustChangePassword()
    ElMessage.success('密码修改成功')
    router.push('/')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || '修改失败，请检查原密码是否正确'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="change-password-page">
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>

    <div class="form-container">
      <div class="form-box">
        <div class="form-header">
          <svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2"/>
            <path d="M7 11V7a5 5 0 0110 0v4"/>
          </svg>
          <h2 class="form-title">修改密码</h2>
          <p class="form-desc">请输入原密码和新密码</p>
        </div>

        <form @submit.prevent="handleSubmit" class="password-form">
          <div class="form-group">
            <label class="form-label">原密码</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2"/>
                <path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
              <input
                v-model="form.oldPassword"
                type="password"
                class="form-input"
                placeholder="请输入原密码"
              />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">新密码</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <input
                v-model="form.newPassword"
                type="password"
                class="form-input"
                placeholder="请输入新密码"
              />
            </div>
            <div class="password-rules">
              <span
                v-for="(rule, idx) in ruleStatus"
                :key="idx"
                class="rule-item"
                :class="{ 'passed': rule.passed === true, 'failed': rule.passed === false }"
              >
                <svg v-if="rule.passed === true" class="rule-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <svg v-else-if="rule.passed === false" class="rule-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
                <span v-else class="rule-dot"></span>
                {{ rule.text }}
              </span>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">确认新密码</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <input
                v-model="form.confirmPassword"
                type="password"
                class="form-input"
                placeholder="请再次输入新密码"
              />
            </div>
          </div>

          <div v-if="errorMsg" class="error-message">
            <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ errorMsg }}
          </div>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="!loading">确认修改</span>
            <span v-else class="loading-text">
              <span class="spinner"></span>
              提交中...
            </span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.change-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  position: relative;
  overflow: hidden;
}

.bg-decoration {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.15);
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  animation: float 6s ease-in-out infinite;
}

.circle-2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  animation: float 8s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}

.form-container {
  position: relative;
  z-index: 1;
}

.form-box {
  background: white;
  border-radius: 24px;
  padding: 48px 40px;
  width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e2e8f0;
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.header-icon {
  width: 48px;
  height: 48px;
  color: #7aaed8;
  margin-bottom: 16px;
}

.form-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.form-desc {
  font-size: 14px;
  color: #888;
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #444;
}

.input-wrapper {
  display: flex;
  align-items: center;
  background: #f7f7fa;
  border: 2px solid transparent;
  border-radius: 12px;
  padding: 0 16px;
  transition: all 0.3s ease;
}

.input-wrapper:focus-within {
  border-color: #7aaed8;
  background: white;
  box-shadow: 0 0 0 4px rgba(122, 174, 216, 0.15);
}

.input-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  margin-right: 12px;
  color: #94a3b8;
}

.form-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 14px 0;
  font-size: 14px;
  color: #333;
  outline: none;
}

.form-input::placeholder {
  color: #aaa;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  margin-top: 8px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #7aaed8 0%, #5a92c4 100%);
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(122, 174, 216, 0.4);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(122, 174, 216, 0.5);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.password-rules {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  padding-left: 4px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #94a3b8;
  transition: color 0.2s;
}

.rule-item.passed {
  color: #22c55e;
}

.rule-item.failed {
  color: #ef4444;
}

.rule-icon {
  width: 14px;
  height: 14px;
}

.rule-dot {
  width: 6px;
  height: 6px;
  background: #cbd5e1;
  border-radius: 50%;
  margin-right: 2px;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
}

.error-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

@media (max-width: 480px) {
  .form-box {
    width: 95%;
    max-width: 400px;
    padding: 32px 24px;
  }
}
</style>
