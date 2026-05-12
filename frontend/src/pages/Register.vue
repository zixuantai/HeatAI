<template>
  <div class="register-page">
    <!-- Left Panel: Animated Characters -->
    <div class="left-panel">
      <div class="left-content">
        <div class="left-top">
          <div class="brand">
            <div class="brand-icon">🔥</div>
            <span class="brand-text">HeatAI</span>
          </div>
        </div>

        <div class="characters-area">
          <AnimatedCharacters
            :is-typing="isTyping"
            :show-password="showPassword || showConfirmPassword"
            :password-length="form.password.length"
          />
        </div>

        <div class="left-footer">
          <span>供热智能客服系统</span>
        </div>
      </div>
      <div class="decor-grid" />
      <div class="decor-blur decor-blur-1" />
      <div class="decor-blur decor-blur-2" />
    </div>

    <!-- Right Panel: Register Form -->
    <div class="right-panel">
      <div class="form-card">
        <div class="mobile-brand">
          <div class="brand-icon">🔥</div>
          <span class="brand-text">HeatAI</span>
        </div>

        <div class="form-header">
          <h1 class="form-title">创建账户</h1>
          <p class="form-subtitle">加入HeatAI，高效解决供热问题</p>
        </div>

        <form class="form-body" @submit.prevent="handleRegister">
          <div class="field-group">
            <label class="field-label" for="username">用户名</label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              class="field-input"
              placeholder="请输入用户名（3-20位字符）"
              autocomplete="off"
              @focus="isTyping = true"
              @blur="isTyping = false"
            />
          </div>

          <div class="field-group">
            <label class="field-label" for="password">密码</label>
            <div class="password-wrapper">
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="field-input"
                placeholder="请输入密码（6-20位字符）"
                @focus="isTyping = true; isPasswordFocused = true"
                @blur="isTyping = false; isPasswordFocused = false"
              />
              <button
                type="button"
                class="toggle-pwd"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </div>
            <div class="password-strength" v-if="form.password">
              <div class="strength-bar">
                <div class="strength-fill" :style="strengthBarStyle" />
              </div>
              <span class="strength-text">{{ passwordStrength.text }}</span>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label" for="password_confirm">确认密码</label>
            <div class="password-wrapper">
              <input
                id="password_confirm"
                v-model="form.password_confirm"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="field-input"
                placeholder="请再次输入密码"
                @focus="isTyping = true"
                @blur="isTyping = false"
              />
              <button
                type="button"
                class="toggle-pwd"
                @click="showConfirmPassword = !showConfirmPassword"
              >
                <svg v-if="showConfirmPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </div>
          </div>

          <InteractiveHoverButton
            type="submit"
            :text="loading ? '注册中...' : '注 册'"
            :loading="loading"
            :disabled="loading"
          />

          <div v-if="errorMsg" class="form-error">
            {{ errorMsg }}
          </div>
        </form>

        <div class="form-footer">
          已有账户？
          <router-link to="/login" class="form-link">立即登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { registerApi } from '@/api/auth'
import { useAuthStore } from '@/store/modules/auth'
import AnimatedCharacters from '@/components/auth/AnimatedCharacters.vue'
import InteractiveHoverButton from '@/components/auth/InteractiveHoverButton.vue'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const errorMsg = ref('')
const isTyping = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const isPasswordFocused = ref(false)

const form = reactive({
  username: '',
  password: '',
  password_confirm: '',
})

const passwordStrength = computed(() => {
  const pwd = form.password
  if (!pwd) return { percent: 0, color: '#e2e8f0', text: '' }

  let score = 0
  if (pwd.length >= 6) score += 25
  if (pwd.length >= 10) score += 15
  if (/[a-z]/.test(pwd)) score += 15
  if (/[A-Z]/.test(pwd)) score += 15
  if (/[0-9]/.test(pwd)) score += 15
  if (/[^a-zA-Z0-9]/.test(pwd)) score += 15

  if (score <= 30) return { percent: 33, color: '#ef4444', text: '弱' }
  if (score <= 60) return { percent: 66, color: '#f59e0b', text: '中' }
  return { percent: 100, color: '#22c55e', text: '强' }
})

const strengthBarStyle = computed(() => ({
  width: `${passwordStrength.value.percent}%`,
  backgroundColor: passwordStrength.value.color,
}))

async function handleRegister() {
  errorMsg.value = ''

  if (!form.username.trim()) { errorMsg.value = '请输入用户名'; return }
  if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$/.test(form.username.trim())) {
    errorMsg.value = '用户名支持字母、数字、下划线和中文，3-20位'
    return
  }
  if (!form.password) { errorMsg.value = '请输入密码'; return }
  if (form.password.length < 6 || form.password.length > 20) {
    errorMsg.value = '密码长度为6-20个字符'
    return
  }
  if (!form.password_confirm) { errorMsg.value = '请确认密码'; return }
  if (form.password !== form.password_confirm) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await registerApi({
      username: form.username.trim(),
      password: form.password,
      password_confirm: form.password_confirm,
    })
    ElMessage.success('注册成功，正在为您跳转...')
    await authStore.login(form.username.trim(), form.password)
    router.push('/chat')
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || '注册失败，请稍后重试'
    errorMsg.value = msg
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  max-height: 100vh;
  overflow: hidden;
}

/* ========== Left Panel ========== */
.left-panel {
  display: none;
  position: relative;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 50%, #4b5563 100%);
  padding: 48px;
  color: #fff;
  overflow: hidden;
}

@media (min-width: 1024px) {
  .left-panel {
    display: flex;
  }
}

.left-content {
  position: relative;
  z-index: 20;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}

.left-top {
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 38px;
  height: 38px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.brand-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.characters-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.left-footer {
  flex-shrink: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

/* Decorative */
.decor-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
  z-index: 0;
}

.decor-blur {
  position: absolute;
  border-radius: 50%;
  filter: blur(64px);
  z-index: 0;
}

.decor-blur-1 {
  top: 25%;
  right: 25%;
  width: 256px;
  height: 256px;
  background: rgba(156, 163, 175, 0.2);
}

.decor-blur-2 {
  bottom: 25%;
  left: 25%;
  width: 384px;
  height: 384px;
  background: rgba(209, 213, 219, 0.15);
}

/* ========== Right Panel ========== */
.right-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: #fff;
}

.form-card {
  width: 100%;
  max-width: 420px;
}

.mobile-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 48px;
}

@media (min-width: 1024px) {
  .mobile-brand {
    display: none;
  }
}

.mobile-brand .brand-icon {
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.mobile-brand .brand-text {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-title {
  font-size: 30px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.form-subtitle {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.field-input {
  height: 48px;
  padding: 0 16px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  font-size: 15px;
  color: #1e293b;
  background: #fff;
  outline: none;
  transition: all 0.2s ease;
  font-family: inherit;
  box-sizing: border-box;
  width: 100%;
}

.field-input::placeholder {
  color: #94a3b8;
}

.field-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.password-wrapper {
  position: relative;
}

.password-wrapper .field-input {
  padding-right: 48px;
}

.toggle-pwd {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}

.toggle-pwd:hover {
  color: #6366f1;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 2px;
}

.strength-bar {
  flex: 1;
  height: 5px;
  background: #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 8px;
  transition: all 0.4s ease;
}

.strength-text {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  min-width: 20px;
  text-align: right;
}

.form-error {
  padding: 12px 16px;
  font-size: 13px;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 18px;
  text-align: center;
}

.form-footer {
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
  margin-top: 28px;
}

.form-link {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.form-link:hover {
  text-decoration: underline;
}

/* ========== Responsive ========== */
@media (max-width: 1023px) {
  .register-page {
    grid-template-columns: 1fr;
  }
}
</style>