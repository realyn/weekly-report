<script setup>
import { useUserStore } from './stores/user'
import { useRouter } from 'vue-router'
import { computed } from 'vue'

const userStore = useUserStore()
const router = useRouter()

const isLoggedIn = computed(() => userStore.isLoggedIn)
const currentUser = computed(() => userStore.user)

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-config-provider>
    <div class="app-container">
      <el-header v-if="isLoggedIn" class="app-header">
        <div class="header-left">
          <h1 class="logo">周报管理系统</h1>
          <el-menu mode="horizontal" router :default-active="$route.path" class="nav-menu">
            <el-menu-item index="/report">填写周报</el-menu-item>
            <el-menu-item index="/summary">周报汇总</el-menu-item>
            <el-menu-item index="/history">历史周报</el-menu-item>
            <el-menu-item v-if="currentUser?.role === 'admin'" index="/admin/users">用户管理</el-menu-item>
          </el-menu>
        </div>
        <div class="header-right">
          <span class="user-name">{{ currentUser?.real_name }}</span>
          <el-button type="text" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </div>
  </el-config-provider>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

.app-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  font-size: 18px;
  color: #409eff;
  margin-right: 40px;
}

.nav-menu {
  border-bottom: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-name {
  color: #606266;
}

.app-main {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
