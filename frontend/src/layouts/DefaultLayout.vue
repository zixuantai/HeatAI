<template>
  <el-container class="layout-container">
    <el-aside :width="collapsed ? '60px' : '320px'" class="layout-aside" :class="{ collapsed }">
      <div class="aside-header">
        <div class="collapse-btn" @click="collapsed = !collapsed">
          <span class="hamburger" :class="{ open: !collapsed }">
            <span></span>
            <span></span>
            <span></span>
          </span>
        </div>
        <div v-show="!collapsed" class="aside-logo">
          <span class="logo-icon">🔥</span>
          <span class="logo-text">HeatAI</span>
        </div>
      </div>
      <el-button type="primary" class="new-chat-btn" @click="handleNewChat">
        <el-icon><Plus /></el-icon>
        <span v-show="!collapsed">新建对话</span>
      </el-button>
      <div v-show="!collapsed" class="session-list">
        <div v-if="sessions.length === 0" class="session-empty">暂无历史对话</div>
        <div
          v-for="sess in sessions"
          :key="sess.id"
          class="session-item"
          :class="{ active: activeSessionId === sess.id }"
          @click="handleSelectSession(sess.id)"
        >
          <div class="session-item-title">{{ sess.title }}</div>
          <div class="session-item-meta">{{ sess.message_count }} 条消息</div>
          <el-popconfirm
            title="确定删除该对话？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm.stop="handleDeleteSession(sess.id)"
          >
            <template #reference>
              <el-icon class="session-delete" @click.stop><Delete /></el-icon>
            </template>
          </el-popconfirm>
        </div>
      </div>

      <div class="aside-spacer"></div>

      <el-popover
        v-model:visible="popoverVisible"
        :width="240"
        trigger="click"
        placement="right-start"
        popper-class="user-menu-popover"
        :disabled="collapsed"
      >
        <template #reference>
          <div class="aside-user" :class="{ 'is-active': popoverVisible }">
            <el-avatar :size="36" icon="UserFilled" />
            <div v-show="!collapsed" class="user-info">
              <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
              <span class="user-role">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</span>
            </div>
            <el-icon v-show="!collapsed" class="user-arrow"><ArrowRight /></el-icon>
          </div>
        </template>
        <div class="user-menu">
          <div class="user-menu-header">
            <el-avatar :size="28" icon="UserFilled" />
            <span class="user-menu-name">{{ authStore.user?.username || '用户' }}</span>
          </div>
          <div class="user-menu-divider"></div>
          <div class="user-menu-item" @click="handleEditProfile">
            <el-icon><Edit /></el-icon>
            <span>修改信息</span>
          </div>
          <div class="user-menu-item user-menu-item--danger" @click="handleLogoutClick">
            <el-icon><SwitchButton /></el-icon>
            <span>退出登录</span>
          </div>
        </div>
      </el-popover>
    </el-aside>
    <el-main class="layout-main">
      <router-view />
    </el-main>
  </el-container>

  <el-dialog v-model="editDialogVisible" title="修改个人信息" width="440px" :close-on-click-modal="false" destroy-on-close>
    <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="70px" class="edit-form">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="editForm.username" maxlength="20" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="昵称" prop="nickname">
        <el-input v-model="editForm.nickname" maxlength="50" placeholder="请输入昵称" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="editForm.email" maxlength="100" placeholder="请输入邮箱" />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input v-model="editForm.phone" maxlength="20" placeholder="请输入手机号" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="editLoading" @click="handleSaveProfile">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Plus, SwitchButton, Edit, ArrowRight, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '@/store/modules/auth'
import { ElMessageBox, ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getSessionsApi, deleteSessionApi } from '@/api/chat'
import type { SessionInfo } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const popoverVisible = ref(false)
const collapsed = ref(false)
const editDialogVisible = ref(false)
const editLoading = ref(false)
const sessions = ref<SessionInfo[]>([])

const activeSessionId = computed(() => {
  return (route.params.sessionId as string) || null
})

const editForm = reactive({
  username: '',
  nickname: '',
  email: '',
  phone: ''
})

const editFormRef = ref<FormInstance>()

const editRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20位', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, message: '用户名支持字母、数字、下划线和中文', trigger: 'blur' }
  ]
}

async function handleLogoutClick() {
  popoverVisible.value = false
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

function handleEditProfile() {
  popoverVisible.value = false
  const user = authStore.user
  editForm.username = user?.username || ''
  editForm.nickname = user?.nickname || ''
  editForm.email = user?.email || ''
  editForm.phone = user?.phone || ''
  editDialogVisible.value = true
}

async function handleSaveProfile() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return

  editLoading.value = true
  try {
    await authStore.updateProfile({
      username: editForm.username,
      nickname: editForm.nickname || null,
      email: editForm.email || null,
      phone: editForm.phone || null
    })
    ElMessage.success('个人信息修改成功')
    editDialogVisible.value = false
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || '修改失败'
    ElMessage.error(msg)
  } finally {
    editLoading.value = false
  }
}

async function loadSessions() {
  try {
    const res = await getSessionsApi(50, 0)
    sessions.value = res.data || []
  } catch {
    // 静默失败
  }
}

function handleNewChat() {
  router.push('/chat')
}

function handleSelectSession(sessionId: string) {
  router.push(`/chat/${sessionId}`)
}

async function handleDeleteSession(sessionId: string) {
  try {
    await deleteSessionApi(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (activeSessionId.value === sessionId) {
      router.push('/chat')
    }
    ElMessage.success('对话已删除')
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || '删除失败'
    ElMessage.error(msg)
  }
}

onMounted(() => {
  loadSessions()
})

watch(() => route.path, () => {
  loadSessions()
})
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
  transition: width 0.25s ease;
  overflow: hidden;
}

.aside-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  border-bottom: 1px solid #2a2a4a;
}

.collapsed .aside-header {
  justify-content: center;
  padding: 20px 0;
}

.collapse-btn {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  transition: background 0.2s;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.hamburger {
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 20px;
}

.hamburger span {
  display: block;
  height: 2px;
  background: #ccc;
  border-radius: 1px;
  transition: all 0.25s ease;
  transform-origin: center;
}

.collapse-btn:hover .hamburger span {
  background: #fff;
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

.new-chat-btn {
  margin: 16px 20px;
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  border: none;
  border-radius: 8px;
  white-space: nowrap;
  overflow: hidden;
}

.collapsed .new-chat-btn {
  margin: 16px 10px;
  padding: 0;
  min-width: 40px;
  justify-content: center;
  height: 40px;
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

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 4px;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.session-item.active {
  background: rgba(255, 107, 53, 0.2);
}

.session-item-title {
  flex: 1;
  font-size: 13px;
  color: #e0e0e0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item.active .session-item-title {
  color: #ff6b35;
}

.session-item-meta {
  font-size: 11px;
  color: #909399;
  flex-shrink: 0;
}

.session-delete {
  font-size: 14px;
  color: #909399;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.session-item:hover .session-delete {
  opacity: 1;
}

.session-delete:hover {
  color: #f56c6c;
}

.aside-spacer {
  flex: 1;
}

.aside-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #2a2a4a;
  cursor: pointer;
  transition: background 0.2s;
  user-select: none;
}

.collapsed .aside-user {
  justify-content: center;
  padding: 12px 0;
}

.aside-user:hover,
.aside-user.is-active {
  background: rgba(255, 255, 255, 0.06);
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 12px;
  color: #909399;
}

.user-arrow {
  font-size: 12px;
  color: #909399;
  transition: transform 0.2s;
}

.aside-user.is-active .user-arrow {
  transform: rotate(90deg);
}

.layout-main {
  background: #f5f5f5;
  padding: 0;
  overflow: hidden;
}

.edit-form {
  padding-top: 10px;
}
</style>

<style>
.user-menu-popover {
  padding: 8px 0 !important;
  background: #fff !important;
  border-radius: 10px !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12) !important;
}

.user-menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px 12px;
}

.user-menu-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.user-menu-divider {
  margin: 0 12px;
  border-top: 1px solid #f0f0f0;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  font-size: 14px;
  color: #303133;
  cursor: pointer;
  transition: background 0.15s;
}

.user-menu-item:hover {
  background: #f5f5f5;
}

.user-menu-item--danger {
  color: #f56c6c;
}

.user-menu-item--danger:hover {
  background: #fef0f0;
}
</style>
