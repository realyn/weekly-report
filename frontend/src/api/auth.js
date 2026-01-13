import request from './request'

export const authApi = {
  login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return request.post('/auth/login', formData)
  },

  getMe() {
    return request.get('/auth/me')
  },

  changePassword(oldPassword, newPassword) {
    return request.put('/auth/password', {
      old_password: oldPassword,
      new_password: newPassword
    })
  }
}
