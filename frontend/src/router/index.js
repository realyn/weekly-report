import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/report'
  },
  {
    path: '/report',
    name: 'Report',
    component: () => import('../views/Report.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/daily-report',
    name: 'DailyReport',
    component: () => import('../views/DailyReport.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/daily-report/history',
    name: 'DailyReportHistory',
    component: () => import('../views/DailyReportHistory.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks',
    name: 'TaskList',
    component: () => import('../views/TaskList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/summary',
    redirect: '/chart'  // 重定向到合并后的页面
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/chart',
    name: 'Chart',
    component: () => import('../views/Chart.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: () => import('../views/Admin/Users.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/projects',
    name: 'AdminProjects',
    component: () => import('../views/Admin/Projects.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('../views/ChangePassword.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (userStore.isLoggedIn && userStore.mustChangePassword && to.path !== '/change-password') {
    // 需要修改密码的用户只能访问修改密码页面
    next('/change-password')
  } else if (to.meta.requiresAdmin && userStore.user?.role !== 'admin') {
    next('/')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
