<template>
  <div class="login-page">
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
            :show-password="showPassword"
            :password-length="passwordLength"
          />
        </div>

        <div class="left-footer">
          <span>供热智能客服系统</span>
        </div>
      </div>
      <!-- Decorative elements -->
      <div class="decor-grid" />
      <div class="decor-blur decor-blur-1" />
      <div class="decor-blur decor-blur-2" />
    </div>

    <!-- Right Panel: Login Form -->
    <div class="right-panel">
      <div class="form-card">
        <div class="mobile-brand">
          <div class="brand-icon">🔥</div>
          <span class="brand-text">HeatAI</span>
        </div>

        <div class="form-header">
          <h1 class="form-title">欢迎回来！</h1>
          <p class="form-subtitle">请输入您的账户信息</p>
        </div>

        <form class="form-body" @submit.prevent="handleLogin">
          <div class="field-group">
            <label class="field-label" for="username">用户名</label>
            <input
              id="username"
              v-model="form.username"
              type="text"
              class="field-input"
              placeholder="请输入用户名"
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
                placeholder="••••••••"
                @focus="isTyping = true"
                @blur="isTyping = false"
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
          </div>

          <div class="form-options">
            <label class="remember-row">
              <input type="checkbox" class="remember-check" />
              <span class="remember-text">记住我</span>
            </label>
          </div>

          <InteractiveHoverButton
            type="submit"
            :text="loading ? '登录中...' : '登 录'"
            :loading="loading"
            :disabled="loading"
          />

          <div v-if="errorMsg" class="form-error">
            {{ errorMsg }}
          </div>
        </form>

        <div class="form-footer">
          还没有账户？
          <router-link to="/register" class="form-link">立即注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/modules/auth'
import AnimatedCharacters from '@/components/auth/AnimatedCharacters.vue'
import InteractiveHoverButton from '@/components/auth/InteractiveHoverButton.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const loading = ref(false)
const errorMsg = ref('')
const isTyping = ref(false)
const showPassword = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const passwordLength = computed(() => form.password.length)

async function handleLogin() {
  if (!form.username.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (form.username.trim().length < 3) {
    errorMsg.value = '用户名至少3个字符'
    return
  }
  if (!form.password) {
    errorMsg.value = '请输入密码'
    return
  }
  if (form.password.length < 6) {
    errorMsg.value = '密码至少6个字符'
    return
  }

  errorMsg.value = ''
  loading.value = true
  try {
    await authStore.login(form.username.trim(), form.password)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect as string
    router.push(redirect || '/chat')
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || '登录失败，请检查用户名和密码'
    errorMsg.value = msg
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
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
  margin-bottom: 40px;
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
  gap: 20px;
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

.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.remember-row {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.remember-check {
  width: 18px;
  height: 18px;
  accent-color: #6366f1;
  cursor: pointer;
}

.remember-text {
  font-size: 14px;
  color: #64748b;
  user-select: none;
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
  margin-top: 32px;
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
  .login-page {
    grid-template-columns: 1fr;
  }
}
</style>