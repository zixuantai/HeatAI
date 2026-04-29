import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types'
import { loginApi, registerApi, refreshTokenApi, getCurrentUserApi, updateCurrentUserApi, logoutApi } from '@/api/auth'
import type { UpdateUserRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    setTokens(res.access_token, res.refresh_token)
    await fetchCurrentUser()
  }

  async function register(username: string, password: string) {
    await registerApi({ username, password, password_confirm: password })
  }

  async function fetchCurrentUser() {
    try {
      const userInfo = await getCurrentUserApi()
      user.value = userInfo
    } catch {
      clearTokens()
      user.value = null
    }
  }

  async function refreshAccessToken() {
    try {
      const res = await refreshTokenApi()
      localStorage.setItem('access_token', res.access_token)
      accessToken.value = res.access_token
    } catch {
      clearTokens()
      user.value = null
    }
  }

  async function logout() {
    try {
      await logoutApi()
    } finally {
      clearTokens()
      user.value = null
    }
  }

  async function updateProfile(data: UpdateUserRequest) {
    const updatedUser = await updateCurrentUserApi(data)
    user.value = updatedUser
  }

  async function initAuth() {
    if (accessToken.value) {
      await fetchCurrentUser()
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isAdmin,
    setTokens,
    clearTokens,
    login,
    register,
    fetchCurrentUser,
    refreshAccessToken,
    logout,
    updateProfile,
    initAuth
  }
})
