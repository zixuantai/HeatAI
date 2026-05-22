import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo, Organization, OrganizationMember } from '@/types'
import { loginApi, registerApi, refreshTokenApi, getCurrentUserApi, updateCurrentUserApi, logoutApi } from '@/api/auth'
import { getMyOrganizationsApi } from '@/api/organizations'
import type { UpdateUserRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const organizations = ref<Organization[]>([])
  const currentOrgId = ref<string | null>(localStorage.getItem('current_org_id'))

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  const currentOrg = computed(() => {
    if (!currentOrgId.value) return null
    return organizations.value.find(o => o.id === currentOrgId.value) || null
  })

  const currentMemberRole = computed(() => {
    if (!user.value?.organizations) return null
    const membership = user.value.organizations.find(
      (m: any) => m.organization_id === currentOrgId.value
    )
    return membership?.role || null
  })

  const isOrgAdmin = computed(() => {
    const role = currentMemberRole.value
    return role === 'owner' || role === 'admin'
  })

  const isOrgEditor = computed(() => {
    const role = currentMemberRole.value
    return role === 'owner' || role === 'admin' || role === 'editor'
  })

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

  function setCurrentOrg(orgId: string | null) {
    currentOrgId.value = orgId
    if (orgId) {
      localStorage.setItem('current_org_id', orgId)
    } else {
      localStorage.removeItem('current_org_id')
    }
  }

  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    setTokens(res.access_token, res.refresh_token)
    await fetchCurrentUser()
    await fetchOrganizations()
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

  async function fetchOrganizations() {
    try {
      const orgs = await getMyOrganizationsApi()
      organizations.value = orgs
      if (currentOrgId.value && !orgs.find(o => o.id === currentOrgId.value)) {
        setCurrentOrg(null)
      }
    } catch {
      organizations.value = []
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
      organizations.value = []
      setCurrentOrg(null)
    }
  }

  async function updateProfile(data: UpdateUserRequest) {
    const updatedUser = await updateCurrentUserApi(data)
    user.value = updatedUser
  }

  async function initAuth() {
    if (accessToken.value) {
      await fetchCurrentUser()
      await fetchOrganizations()
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    organizations,
    currentOrgId,
    isAuthenticated,
    isAdmin,
    currentOrg,
    currentMemberRole,
    isOrgAdmin,
    isOrgEditor,
    setTokens,
    clearTokens,
    setCurrentOrg,
    login,
    register,
    fetchCurrentUser,
    fetchOrganizations,
    refreshAccessToken,
    logout,
    updateProfile,
    initAuth
  }
})
