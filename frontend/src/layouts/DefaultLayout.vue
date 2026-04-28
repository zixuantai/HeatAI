<template>
  <el-container class="layout-container">
    <el-aside width="280px" class="layout-aside">
      <div class="aside-header">
        <div class="aside-logo">
          <span class="logo-icon">🔥</span>
          <span class="logo-text">HeatAI</span>
        </div>
      </div>
      <div class="aside-user">
        <el-avatar :size="36" icon="UserFilled" />
        <div class="user-info">
          <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
          <span class="user-role">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</span>
        </div>
        <el-button
          text
          type="danger"
          :icon="SwitchButton"
          @click="handleLogout"
        />
      </div>
      <el-button type="primary" class="new-chat-btn" @click="handleNewChat">
        <el-icon><Plus /></el-icon>
        新建对话
      </el-button>
      <div class="session-list">
        <div class="session-empty">暂无历史对话</div>
      </div>
    </el-aside>
    <el-main class="layout-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { SwitchButton, Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/store/modules/auth'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await authStore.logout()
    router.push('/login')
  } catch {
    // 用户取消
  }
}

function handleNewChat() {
  // 后续实现
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-aside {
  background: #1a1a2e;
  color: #fff;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #2a2a4a;
}

.aside-header {
  padding: 20px;
  border-bottom: 1px solid #2a2a4a;
}

.aside-logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  color: #ff6b35;
}

.aside-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a4a;
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

.user-role {
  font-size: 12px;
  color: #909399;
}

.new-chat-btn {
  margin: 16px 20px;
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  border: none;
  border-radius: 8px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.session-empty {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 40px 0;
}

.layout-main {
  background: #f5f5f5;
  padding: 0;
  overflow: hidden;
}
</style>
