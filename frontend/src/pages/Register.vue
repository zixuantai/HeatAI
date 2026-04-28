<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <EyeFollow :is-focused="hasAnyFocus" :is-password="isPasswordFocused" />
        <h1 class="auth-title">创建账户</h1>
        <p class="auth-subtitle">加入HeatAI，高效解决供热问题</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="auth-form"
        @keyup.enter="handleRegister"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名（3-20位字符）"
            :prefix-icon="User"
            size="large"
            @focus="isPasswordFocused = false; hasAnyFocus = true"
            @blur="handleBlur"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码（6-20位字符）"
            :prefix-icon="Lock"
            size="large"
            show-password
            @focus="isPasswordFocused = true; hasAnyFocus = true"
            @blur="handleBlur"
          />
        </el-form-item>

        <el-form-item prop="password_confirm">
          <el-input
            v-model="form.password_confirm"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @focus="isPasswordFocused = true; hasAnyFocus = true"
            @blur="handleBlur"
          />
        </el-form-item>

        <div class="password-tips">
          <el-progress
            :percentage="passwordStrength.percent"
            :color="passwordStrength.color"
            :stroke-width="6"
            :show-text="false"
          />
          <span class="strength-text">{{ passwordStrength.text }}</span>
        </div>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleRegister"
          >
            注 册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        已有账户？
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { registerApi } from '@/api/auth'
import { useAuthStore } from '@/store/modules/auth'
import EyeFollow from '@/components/auth/EyeFollow.vue'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const isPasswordFocused = ref(false)
const hasAnyFocus = ref(false)

const form = reactive({
  username: '',
  password: '',
  password_confirm: ''
})

function handleBlur() {
  setTimeout(() => {
    hasAnyFocus.value = false
    isPasswordFocused.value = false
  }, 150)
}

const validateUsername = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (!value) {
    callback(new Error('请输入用户名'))
    return
  }
  if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$/.test(value)) {
    callback(new Error('用户名支持字母、数字、下划线和中文，3-20位'))
    return
  }
  callback()
}

const validatePasswordConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const rules: FormRules = {
  username: [
    { required: true, validator: validateUsername, trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, validator: validatePasswordConfirm, trigger: 'blur' }
  ]
}

const passwordStrength = computed(() => {
  const pwd = form.password
  if (!pwd) return { percent: 0, color: '#e6e6e6', text: '' }

  let score = 0
  if (pwd.length >= 6) score += 25
  if (pwd.length >= 10) score += 15
  if (/[a-z]/.test(pwd)) score += 15
  if (/[A-Z]/.test(pwd)) score += 15
  if (/[0-9]/.test(pwd)) score += 15
  if (/[^a-zA-Z0-9]/.test(pwd)) score += 15

  if (score <= 30) return { percent: 33, color: '#f56c6c', text: '弱' }
  if (score <= 60) return { percent: 66, color: '#e6a23c', text: '中' }
  return { percent: 100, color: '#67c23a', text: '强' }
})

async function handleRegister() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await registerApi({
        username: form.username,
        password: form.password,
        password_confirm: form.password_confirm
      })
      ElMessage.success('注册成功，正在为您跳转...')
      await authStore.login(form.username, form.password)
      router.push('/chat')
    } catch {
      // 错误已在请求拦截器中处理
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.auth-header {
  padding: 36px 40px 0;
}

.auth-title {
  margin-top: 4px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  border: none;
  border-radius: 8px;
  letter-spacing: 4px;
}

.submit-btn:hover {
  background: linear-gradient(135deg, #e55d2b, #e6840e);
}

.password-tips {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 0 4px;
}

.password-tips .el-progress {
  flex: 1;
}

.strength-text {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  min-width: 20px;
}
</style>
