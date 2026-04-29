<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <EyeFollow :is-focused="hasAnyFocus" :is-password="isPasswordFocused" />
        <h1 class="auth-title">HeatAI</h1>
        <p class="auth-subtitle">供热智能客服系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="auth-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
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
            placeholder="请输入密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @focus="isPasswordFocused = true; hasAnyFocus = true"
            @blur="handleBlur"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        还没有账户？
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/store/modules/auth'
import EyeFollow from '@/components/auth/EyeFollow.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const isPasswordFocused = ref(false)
const hasAnyFocus = ref(false)

const form = reactive({
  username: '',
  password: ''
})

function handleBlur() {
  setTimeout(() => {
    hasAnyFocus.value = false
    isPasswordFocused.value = false
  }, 150)
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度为6-20个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return

  try {
    await formRef.value.validateField('username')
  } catch {
    return
  }

  try {
    await formRef.value.validateField('password')
  } catch {
    return
  }

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect as string
    router.push(redirect || '/chat')
  } catch {
    // 错误已在请求拦截器中处理
  } finally {
    loading.value = false
  }
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
</style>
