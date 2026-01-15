import axios from 'axios'
import { ElMessage } from 'element-plus'

const baseURL = import.meta.env.BASE_URL === '/' ? '/api' : `${import.meta.env.BASE_URL}api`

const request = axios.create({
  baseURL,
  timeout: 10000
})

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

request.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    if (error.response?.status === 401) {
      // 登录请求失败由 Login.vue 自己处理，不在这里显示
      if (!error.config?.url?.includes('/auth/login')) {
        // 其他 401 错误，清除登录状态并跳转
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('mustChangePassword')
        const basePath = import.meta.env.BASE_URL === '/' ? '' : import.meta.env.BASE_URL.slice(0, -1)
        window.location.href = `${basePath}/login`
      }
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default request
