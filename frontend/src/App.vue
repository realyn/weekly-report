<script setup>
import { useUserStore } from './stores/user'
import { useRouter, useRoute } from 'vue-router'
import { computed, ref } from 'vue'

// 自定义 v-click-outside 指令
const vClickOutside = {
  mounted(el, binding) {
    el._clickOutside = (e) => {
      if (!el.contains(e.target)) {
        binding.value()
      }
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el) {
    document.removeEventListener('click', el._clickOutside)
  }
}

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const isLoggedIn = computed(() => userStore.isLoggedIn)
const currentUser = computed(() => userStore.user)
const isLoginPage = computed(() => route.path === '/login')
const showUserMenu = ref(false)

const menuItems = [
  { path: '/report', icon: 'edit', label: '填写周报' },
  { path: '/chart', icon: 'chart', label: '周报汇总' },
  { path: '/history', icon: 'clock', label: '历史周报' }
]

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const goChangePassword = () => {
  showUserMenu.value = false
  router.push('/change-password')
}

const handleLogout = () => {
  showUserMenu.value = false
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-wrapper" :class="{ 'login-page': isLoginPage }">
    <!-- 顶部导航栏 -->
    <header v-if="isLoggedIn && !isLoginPage" class="app-header">
      <div class="header-container">
        <div class="header-left">
          <div class="logo">
            <span class="logo-text">周报管理系统</span>
          </div>
          <nav class="nav-menu">
            <router-link
              v-for="item in menuItems"
              :key="item.path"
              :to="item.path"
              class="nav-item"
              :class="{ active: $route.path === item.path }"
            >
              <!-- 填写周报 -->
              <svg v-if="item.icon === 'edit'" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
              <!-- 周报汇总 -->
              <svg v-if="item.icon === 'chart'" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 20V10M12 20V4M6 20v-6"/>
              </svg>
              <!-- 历史周报 -->
              <svg v-if="item.icon === 'clock'" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
              <span class="nav-label">{{ item.label }}</span>
            </router-link>
            <router-link
              v-if="currentUser?.role === 'admin'"
              to="/admin/projects"
              class="nav-item"
              :class="{ active: $route.path === '/admin/projects' }"
            >
              <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"/>
              </svg>
              <span class="nav-label">项目管理</span>
            </router-link>
            <router-link
              v-if="currentUser?.role === 'admin'"
              to="/admin/users"
              class="nav-item"
              :class="{ active: $route.path === '/admin/users' }"
            >
              <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="7" r="4"/>
                <path d="M5.5 21a8.5 8.5 0 0113 0"/>
              </svg>
              <span class="nav-label">用户管理</span>
            </router-link>
          </nav>
        </div>
        <div class="header-right">
          <div class="user-dropdown" v-click-outside="closeUserMenu">
            <button class="user-btn" @click="toggleUserMenu">
              <span class="user-name">{{ currentUser?.real_name }}</span>
              <svg class="dropdown-icon" :class="{ open: showUserMenu }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </button>
            <div class="user-menu" v-show="showUserMenu">
              <button class="menu-item" @click="goChangePassword">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2"/>
                  <path d="M7 11V7a5 5 0 0110 0v4"/>
                </svg>
                <span>修改密码</span>
              </button>
              <button class="menu-item" @click="handleLogout">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
                </svg>
                <span>退出登录</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="app-main" :class="{ 'with-header': isLoggedIn && !isLoginPage }">
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-wrapper {
  min-height: 100vh;
  background: #f8fafc;
}

.app-wrapper.login-page {
  background: #f1f5f9;
}

/* 顶部导航栏 */
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border-bottom: 1px solid #e2e8f0;
}

.header-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}


.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.nav-menu {
  display: flex;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 6px;
  text-decoration: none;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: #f1f5f9;
  color: #334155;
}

.nav-item.active {
  background: #f1f5f9;
  color: #64748b;
}

.nav-icon {
  width: 18px;
  height: 18px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.nav-label {
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-dropdown {
  position: relative;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #334155;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.user-btn:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.user-name {
  white-space: nowrap;
}

.dropdown-icon {
  width: 16px;
  height: 16px;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.2s ease;
}

.dropdown-icon.open {
  transform: rotate(180deg);
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 140px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 6px;
  z-index: 100;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.menu-item:hover {
  background: #f1f5f9;
  color: #334155;
}

.menu-icon {
  width: 16px;
  height: 16px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* 主内容区 */
.app-main {
  min-height: 100vh;
}

.app-main.with-header {
  padding-top: 56px;
}

/* Element Plus 样式覆盖 */
.el-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.el-card__header {
  border-bottom: 1px solid #f1f5f9;
  padding: 16px 20px;
}

.el-button--primary {
  background: #7aaed8;
  border: none;
  border-radius: 8px;
}

.el-button--primary:hover {
  background: #4a9bc4;
}

.el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.el-tag--success {
  background: #dcfce7;
  color: #16a34a;
  border: none;
  border-radius: 6px;
}

.el-tag--info {
  background: #ede9fe;
  color: #64748b;
  border: none;
  border-radius: 6px;
}

.el-table th.el-table__cell {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: 0.05em;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: #f8fafc;
}

/* 响应式 */
@media (max-width: 1024px) {
  .nav-label {
    display: none;
  }

  .nav-item {
    padding: 8px 10px;
  }

  .header-left {
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .logo-text {
    display: none;
  }

  .header-container {
    padding: 0 16px;
  }

  .user-btn .user-name {
    display: none;
  }

  .user-btn {
    padding: 8px;
  }

  .dropdown-icon {
    display: none;
  }

  .user-btn::before {
    content: '';
    width: 20px;
    height: 20px;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' fill='none' stroke='%23475569' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3Cpath d='M5.5 21a8.5 8.5 0 0113 0'/%3E%3C/svg%3E");
    background-size: contain;
  }
}
</style>
