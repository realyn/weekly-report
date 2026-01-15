import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const mustChangePassword = ref(localStorage.getItem('mustChangePassword') === 'true')

  const isLoggedIn = computed(() => !!token.value)

  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  const setUser = (userData) => {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const setMustChangePassword = (value) => {
    mustChangePassword.value = value
    localStorage.setItem('mustChangePassword', value.toString())
  }

  const login = async (username, password) => {
    const response = await authApi.login(username, password)
    setToken(response.access_token)
    const userInfo = await authApi.getMe()
    setUser(userInfo)
    setMustChangePassword(response.must_change_password)
    return { userInfo, mustChangePassword: response.must_change_password }
  }

  const logout = () => {
    token.value = ''
    user.value = null
    mustChangePassword.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('mustChangePassword')
  }

  const clearMustChangePassword = () => {
    mustChangePassword.value = false
    localStorage.removeItem('mustChangePassword')
  }

  return {
    token,
    user,
    mustChangePassword,
    isLoggedIn,
    login,
    logout,
    setUser,
    clearMustChangePassword
  }
})
