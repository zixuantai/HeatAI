<template>
  <el-container class="layout-container">
    <el-aside :width="collapsed ? '60px' : '320px'" class="layout-aside" :class="{ collapsed }">
      <div class="aside-header" :class="{ collapsed }">
        <div class="brand-area">
          <span class="brand-icon">🔥</span>
        </div>
        <el-tooltip :content="collapsed ? '展开侧边栏' : '收起侧边栏'" placement="right" :show-after="300">
          <div class="collapse-btn" @click="collapsed = !collapsed">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
          </div>
        </el-tooltip>
      </div>
      <div class="nav-section">
        <el-tooltip content="新对话" placement="right" :disabled="!collapsed" :show-after="300">
          <div
            class="nav-item"
            :class="{ active: isNewChatRoute }"
            @click="handleNewChat"
          >
            <el-icon :size="20"><ChatDotRound /></el-icon>
            <span v-show="!collapsed">新对话</span>
          </div>
        </el-tooltip>
        <el-tooltip content="知识库" placement="right" :disabled="!collapsed" :show-after="300">
          <div
            class="nav-item"
            :class="{ active: isDocumentsRoute }"
            @click="handleNavToDocuments"
          >
            <el-icon :size="20"><FolderOpened /></el-icon>
            <span v-show="!collapsed">知识库</span>
          </div>
        </el-tooltip>
        <el-tooltip content="搜索对话" placement="right" :disabled="!collapsed" :show-after="300">
          <div
            class="nav-item"
            @click="searchDialogVisible = true"
          >
            <el-icon :size="20"><Search /></el-icon>
            <span v-show="!collapsed">搜索对话</span>
          </div>
        </el-tooltip>
      </div>
      <div v-show="!collapsed" class="session-list">
        <div v-if="sessions.length === 0" class="session-empty">暂无历史对话</div>
        <template v-for="group in sessionGroups" :key="group.key">
          <div v-if="group.label" class="session-date-label">{{ group.label }}</div>
          <div
            v-for="sess in group.sessions"
            :key="sess.id"
            class="session-item"
            :class="{ active: activeSessionId === sess.id, pinned: sess.is_pinned }"
            @click="handleSelectSession(sess.id)"
          >
            <div class="session-item-title">{{ sess.title }}</div>
            <span v-if="sess.is_pinned" class="session-pin-icon" @click.stop="handleTogglePin(sess)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="17" x2="12" y2="22"/>
                <path d="M5 17h14v-1.17a2 2 0 0 0-.59-1.42L17 13V5a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v8l-1.41 1.41A2 2 0 0 0 5 15.83V17z"/>
              </svg>
            </span>
            <el-popover
              v-model:visible="sessionMenuVisible[sess.id]"
              :width="160"
              trigger="click"
              placement="bottom-start"
              popper-class="session-menu-popover"
            >
              <template #reference>
                <button class="session-more-btn" @click.stop>
                  <el-icon :size="18"><MoreFilled /></el-icon>
                </button>
              </template>
              <div class="session-menu">
                <div class="session-menu-item" @click.stop="handleTogglePin(sess)">
                  <span class="session-menu-pin-icon">
                    <svg v-if="!sess.is_pinned" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="12" y1="17" x2="12" y2="22"/>
                      <path d="M5 17h14v-1.17a2 2 0 0 0-.59-1.42L17 13V5a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v8l-1.41 1.41A2 2 0 0 0 5 15.83V17z"/>
                    </svg>
                    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="12" y1="17" x2="12" y2="22"/>
                      <path d="M5 17h14v-1.17a2 2 0 0 0-.59-1.42L17 13V5a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v8l-1.41 1.41A2 2 0 0 0 5 15.83V17z"/>
                      <line x1="2" y1="2" x2="22" y2="22"/>
                    </svg>
                  </span>
                  <span>{{ sess.is_pinned ? '取消置顶' : '置顶' }}</span>
                </div>
                <div class="session-menu-item" @click.stop="handleRenameClick(sess)">
                  <el-icon><Edit /></el-icon>
                  <span>重命名</span>
                </div>
                <div class="session-menu-divider"></div>
                <div class="session-menu-item session-menu-item--danger" @click.stop="handleDeleteClick(sess)">
                  <el-icon><Delete /></el-icon>
                  <span>删除对话</span>
                </div>
              </div>
            </el-popover>
          </div>
        </template>
      </div>

      <div class="user-area-wrapper" ref="userAreaRef">
        <el-tooltip :content="authStore.user?.username || '用户'" placement="right" :disabled="!collapsed" :show-after="300">
          <div class="aside-user" :class="{ 'is-active': popoverVisible }" @click="toggleUserMenu">
            <el-avatar :size="36" icon="UserFilled" />
            <div v-show="!collapsed" class="user-info">
              <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
              <span class="user-role">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</span>
            </div>
            <el-icon v-show="!collapsed" class="user-arrow"><ArrowRight /></el-icon>
          </div>
        </el-tooltip>
      </div>
    </el-aside>
    <el-main class="layout-main">
      <router-view />
    </el-main>
  </el-container>

  <Teleport to="body">
    <div v-if="popoverVisible" class="user-dropdown" :style="dropdownStyle" @click.stop>
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
  </Teleport>

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

  <el-dialog v-model="searchDialogVisible" title="搜索对话" width="620px" :close-on-click-modal="false" destroy-on-close @opened="handleSearchDialogOpened">
    <div class="search-dialog-body">
      <el-input
        ref="searchInputRef"
        v-model="searchKeyword"
        placeholder="搜索历史对话…"
        clearable
        :prefix-icon="Search"
        size="large"
        class="search-dialog-input"
        @input="handleSearchInput"
      />
      <div class="search-new-chat" @click="handleSearchNewChat">
        <el-icon :size="18"><ChatDotRound /></el-icon>
        <span>新对话</span>
      </div>
      <div class="search-results">
        <div v-if="!searchKeyword && filteredSessions.length > 0" class="search-section-label">最近</div>
        <div v-if="filteredSessions.length === 0" class="search-empty">
          {{ searchKeyword ? '未找到匹配的对话' : '暂无历史对话' }}
        </div>
        <div
          v-for="sess in filteredSessions"
          :key="sess.id"
          class="search-result-item"
          :class="{ active: activeSessionId === sess.id }"
          @click="handleSearchSelect(sess.id)"
        >
          <div class="search-result-title">{{ sess.title }}</div>
          <div class="search-result-meta">
            <span>{{ formatYearMonth(sess.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { SwitchButton, Edit, ArrowRight, Delete, ChatDotRound, FolderOpened, MoreFilled, Search } from '@element-plus/icons-vue'
import { useAuthStore } from '@/store/modules/auth'
import { ElMessageBox, ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getSessionsApi, deleteSessionApi, updateSessionTitleApi, togglePinSessionApi } from '@/api/chat'
import type { SessionInfo } from '@/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const popoverVisible = ref(false)
const collapsed = ref(false)
const userAreaRef = ref<HTMLElement | null>(null)
const dropdownStyle = ref<Record<string, string>>({})
const sessionMenuVisible = ref<Record<string, boolean>>({})
const editDialogVisible = ref(false)
const editLoading = ref(false)
const sessions = ref<SessionInfo[]>([])
const searchDialogVisible = ref(false)
const searchKeyword = ref('')
const searchInputRef = ref<any>()

const activeSessionId = computed(() => {
  return (route.params.sessionId as string) || null
})

const isChatRoute = computed(() => {
  return route.path.startsWith('/chat')
})

const isNewChatRoute = computed(() => {
  return route.path === '/chat'
})

const isDocumentsRoute = computed(() => {
  return route.path.startsWith('/documents')
})

function formatYearMonth(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const sessionGroups = computed(() => {
  const groups: { key: string; label: string; sessions: SessionInfo[] }[] = []
  const pinned: SessionInfo[] = []
  const unpinned: SessionInfo[] = []
  for (const sess of sessions.value) {
    if (sess.is_pinned) pinned.push(sess)
    else unpinned.push(sess)
  }
  pinned.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
  unpinned.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
  if (pinned.length > 0) {
    groups.push({ key: '__pinned__', label: '', sessions: pinned })
  }
  for (const sess of unpinned) {
    const label = formatYearMonth(sess.created_at)
    const last = groups[groups.length - 1]
    if (last && last.label === label) {
      last.sessions.push(sess)
    } else {
      groups.push({ key: label, label, sessions: [sess] })
    }
  }
  return groups
})

const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return sessions.value.slice(0, 20)
  }
  return sessions.value.filter(s => s.title.toLowerCase().includes(keyword))
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

function toggleUserMenu() {
  if (collapsed.value) return
  if (!popoverVisible.value && userAreaRef.value) {
    const rect = userAreaRef.value.getBoundingClientRect()
    dropdownStyle.value = {
      position: 'fixed',
      left: rect.right + 8 + 'px',
      bottom: (window.innerHeight - rect.bottom) + 'px',
    }
  }
  popoverVisible.value = !popoverVisible.value
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
    sessions.value = await getSessionsApi(50, 0)
  } catch {
    // 静默失败
  }
}

function handleNewChat() {
  router.push('/chat')
}

function handleNavToDocuments() {
  router.push('/documents')
}

function handleSelectSession(sessionId: string) {
  router.push(`/chat/${sessionId}`)
}

async function handleDeleteClick(sess: SessionInfo) {
  sessionMenuVisible.value[sess.id] = false
  try {
    await ElMessageBox.confirm('确定删除该对话？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await handleDeleteSession(sess.id)
  } catch {
    // 用户取消
  }
}

async function handleTogglePin(sess: SessionInfo) {
  sessionMenuVisible.value[sess.id] = false
  const newPinned = !sess.is_pinned
  try {
    await togglePinSessionApi(sess.id, newPinned)
    await loadSessions()
  } catch {
    // revert silently
  }
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

async function handleRenameClick(sess: SessionInfo) {
  sessionMenuVisible.value[sess.id] = false
  try {
    const { value } = await ElMessageBox.prompt('', '重命名对话', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: sess.title,
      inputMaxlength: 200,
      closeOnClickModal: false
    })
    const title = (value || '').trim()
    if (!title) return
    await updateSessionTitleApi(sess.id, title)
    const found = sessions.value.find(s => s.id === sess.id)
    if (found) {
      found.title = title
    }
    ElMessage.success('重命名成功')
  } catch {
    // 用户取消
  }
}

function handleSearchDialogOpened() {
  searchKeyword.value = ''
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

function handleSearchInput() {
  // reactive, handled by computed
}

function handleSearchSelect(sessionId: string) {
  searchDialogVisible.value = false
  router.push(`/chat/${sessionId}`)
}

function handleSearchNewChat() {
  searchDialogVisible.value = false
  router.push('/chat')
}

function handleClickOutside(e: MouseEvent) {
  if (popoverVisible.value && userAreaRef.value && !userAreaRef.value.contains(e.target as Node)) {
    popoverVisible.value = false
  }
}

onMounted(() => {
  loadSessions()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

watch(() => route.path, () => {
  loadSessions()
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

/* ── Sidebar ─────────────────────────────────────────── */
.layout-aside {
  background: var(--color-surface);
  color: var(--color-text-main);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  box-shadow: 2px 0 24px rgba(79, 70, 229, 0.06);
  transition: width var(--transition-base);
  overflow: hidden;
  position: relative;
  z-index: 10;
}

/* ── Sidebar Header ──────────────────────────────────── */
.aside-header {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  border-bottom: 1px solid var(--color-border);
}

.aside-header.collapsed {
  justify-content: center;
  padding: 20px 0;
}

.aside-header.collapsed .brand-area {
  display: flex;
  padding: 0;
}

.aside-header.collapsed .collapse-btn {
  display: none;
}

.aside-header.collapsed:hover .brand-area {
  display: none;
}

.aside-header.collapsed:hover .collapse-btn {
  display: flex;
}

.collapse-btn {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 37px;
  height: 37px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--color-border);
  box-sizing: border-box;
  transition: background var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast);
  flex-shrink: 0;
  margin-left: auto;
  color: var(--color-text-muted);
  background: var(--color-bg);
}

.aside-header.collapsed .collapse-btn {
  margin-left: 0;
}

.collapse-btn:hover {
  background: var(--gradient-subtle);
  color: var(--color-primary);
  border-color: var(--color-primary);
}

/* ── Brand Area ──────────────────────────────────────── */
.brand-area {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}

.brand-icon {
  width: 37px;
  height: 37px;
  background: var(--gradient-primary);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  color: #fff;
  flex-shrink: 0;
  border: 1.5px solid transparent;
  box-sizing: border-box;
}

.brand-name {
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  letter-spacing: var(--tracking-tight);
  white-space: nowrap;
}

/* ── Navigation ──────────────────────────────────────── */
.nav-section {
  padding: 16px 12px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-base);
  margin-bottom: 2px;
}

.nav-item:hover {
  background: var(--gradient-subtle);
  color: var(--color-primary);
}

.nav-item.active {
  background: var(--gradient-subtle);
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
  box-shadow: var(--shadow-sm);
}

.collapsed .nav-section {
  padding: 16px 8px 8px;
}

.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
  gap: 0;
}

/* ── Session List ────────────────────────────────────── */
.session-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 12px 8px;
}

.session-empty {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  padding: 40px 0;
}

.session-date-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-semibold);
  padding: 12px 14px 6px;
  letter-spacing: 0.04em;
}

.session-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast), box-shadow var(--transition-fast);
  margin-bottom: 3px;
}

.session-item:hover {
  background: var(--color-bg);
}

.session-item.pinned {
  background: var(--color-bg);
}

.session-item.active {
  background: var(--gradient-subtle);
  box-shadow: var(--shadow-sm);
}

.session-item-title {
  flex: 1;
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: var(--font-weight-medium);
  padding-right: 40px;
}

.session-pin-icon {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: right var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
  z-index: 1;
}

.session-pin-icon:hover {
  color: var(--color-primary);
  background: var(--color-bg);
}

.session-item:hover .session-pin-icon {
  right: 48px;
}

.session-item.active .session-item-title {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.session-more-btn {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 30px;
  border-radius: var(--radius-xs);
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--transition-fast), background var(--transition-fast), color var(--transition-fast);
  padding: 0;
  z-index: 2;
}

.session-item:hover .session-more-btn {
  opacity: 1;
}

.session-more-btn:hover {
  background: var(--color-bg);
  color: var(--color-text-main);
}

/* ── User Area ───────────────────────────────────────── */
.user-area-wrapper {
  position: relative;
  flex-shrink: 0;
  margin-top: auto;
}

.aside-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background var(--transition-fast);
  user-select: none;
  flex-shrink: 0;
}

.collapsed .aside-user {
  justify-content: center;
  padding: 12px 0;
}

.aside-user:hover,
.aside-user.is-active {
  background: var(--gradient-subtle);
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.user-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.user-arrow {
  font-size: 12px;
  color: var(--color-text-muted);
  transition: transform var(--transition-fast);
}

.aside-user.is-active .user-arrow {
  transform: rotate(90deg);
}

/* ── Main Content ────────────────────────────────────── */
.layout-main {
  background: var(--color-bg);
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
  background: var(--color-surface) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-card-hover) !important;
  border: 1px solid var(--color-border-light) !important;
}

.user-dropdown {
  width: 240px;
  padding: 8px 0;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card-hover);
  border: 1px solid var(--color-border-light);
  z-index: 1000;
}

.user-menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px 12px;
}

.user-menu-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
}

.user-menu-divider {
  margin: 4px 12px;
  border-top: 1px solid var(--color-border);
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
  font-weight: var(--font-weight-medium);
}

.user-menu-item:hover {
  background: var(--gradient-subtle);
  color: var(--color-primary);
}

.user-menu-item--danger {
  color: #ef4444;
}

.user-menu-item--danger:hover {
  background: #fef2f2;
  color: #dc2626;
}

/* ── Session Menu Popover ─────────────────────────────── */
.session-menu-popover {
  padding: 6px 0 !important;
  background: var(--color-surface) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: var(--shadow-card-hover) !important;
  border: 1px solid var(--color-border-light) !important;
  min-width: 140px !important;
}

.session-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 16px;
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
  font-weight: var(--font-weight-medium);
}

.session-menu-item:hover {
  background: var(--gradient-subtle);
  color: var(--color-primary);
}

.session-menu-item--danger {
  color: #ef4444;
}

.session-menu-item--danger:hover {
  background: #fef2f2;
  color: #dc2626;
}

.session-menu-pin-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.session-menu-divider {
  margin: 4px 12px;
  border-top: 1px solid var(--color-border);
}

/* ── Search Dialog ────────────────────────────────────── */
.search-dialog-input {
  margin-bottom: 12px;
}

.search-new-chat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  margin-bottom: 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
}

.search-new-chat:hover {
  background: var(--gradient-subtle);
  color: var(--color-primary);
}

.search-results {
  max-height: 360px;
  overflow-y: auto;
}

.search-section-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-semibold);
  padding: 12px 16px 4px;
  letter-spacing: 0.04em;
}

.search-empty {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  padding: 32px 0;
}

.search-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.search-result-item:hover {
  background: var(--gradient-subtle);
}

.search-result-item.active {
  background: var(--gradient-subtle);
}

.search-result-title {
  flex: 1;
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  font-weight: var(--font-weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 16px;
}

.search-result-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  flex-shrink: 0;
}
</style>
