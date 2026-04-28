import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/modules/auth'
import type { LoginRequest, RegisterRequest } from '@/types'

export function useAuth() {
  const router = useRouter()
  const authStore = useAuthStore()
  const loading = ref(false)
  const error = ref('')

  async function login(data: LoginRequest) {
    loading.value = true
    error.value = ''
    try {
      await authStore.login(data.username, data.password)
      router.push('/chat')
    } catch (e: unknown) {
      error.value = (e as { message?: string })?.message || '登录失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterRequest) {
    loading.value = true
    error.value = ''
    try {
      await authStore.register(data.username, data.password)
    } catch (e: unknown) {
      error.value = (e as { message?: string })?.message || '注册失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    await authStore.logout()
    router.push('/login')
  }

  return {
    loading,
    error,
    login,
    register,
    logout
  }
}
