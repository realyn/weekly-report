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
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      const basePath = import.meta.env.BASE_URL === '/' ? '' : import.meta.env.BASE_URL.slice(0, -1)
      window.location.href = `${basePath}/login`
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default request
