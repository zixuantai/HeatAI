<template>
  <el-container class="layout-container">
    <el-aside :width="collapsed ? '60px' : '320px'" class="layout-aside" :class="{ collapsed }">
      <div class="aside-header" :class="{ collapsed }">
        <div class="brand-area">
          <span class="brand-icon">🔥</span>
          <span v-show="!collapsed" class="brand-name">HeatAI</span>
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
        <el-tooltip content="搜索对话" placement="right" :disabled="!collapsed" :show-after="300">
          <div
            class="nav-item"
            @click="handleSearchConversations"
          >
            <el-icon :size="20"><Search /></el-icon>
            <span v-show="!collapsed">搜索对话</span>
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
        <el-tooltip content="组织" placement="right" :disabled="!collapsed" :show-after="300">
          <div
            class="nav-item"
            :class="{ active: isOrganizationsRoute }"
            @click="handleNavToOrganizations"
          >
            <el-icon :size="20"><OfficeBuilding /></el-icon>
            <span v-show="!collapsed">组织</span>
          </div>
        </el-tooltip>
        <el-tooltip content="知识库广场" placement="right" :disabled="!collapsed" :show-after="300">
          <div
            class="nav-item"
            :class="{ active: isPlazaRoute }"
            @click="handleNavToPlaza"
          >
            <el-icon :size="20"><Promotion /></el-icon>
            <span v-show="!collapsed">知识库广场</span>
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
            <el-tooltip
              :content="sess.title"
              placement="top"
              :show-after="500"
              :disabled="sess.title.length < 15"
            >
              <div class="session-item-title">{{ sess.title }}</div>
            </el-tooltip>
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
        <el-tooltip :content="authStore.isAuthenticated ? (authStore.user?.username || '用户') : '未登录'" placement="right" :disabled="!collapsed" :show-after="300">
          <div class="aside-user" :class="{ 'is-active': popoverVisible }" @click="handleUserAreaClick">
            <el-avatar :size="36" :src="authStore.user?.avatar || undefined" icon="UserFilled" />
            <div v-show="!collapsed" class="user-info">
              <span class="user-name">{{ authStore.isAuthenticated ? (authStore.user?.username || '用户') : '未登录' }}</span>
              <span class="user-role">{{ authStore.isAuthenticated ? (authStore.isAdmin ? '管理员' : '普通用户') : '' }}</span>
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
        <el-avatar :size="28" :src="authStore.user?.avatar || undefined" icon="UserFilled" />
        <span class="user-menu-name">{{ authStore.user?.username || '用户' }}</span>
      </div>
      <div class="user-menu-divider"></div>
      <div class="user-menu-item" @click="handleEditProfile">
        <el-icon><User /></el-icon>
        <span>个人信息</span>
      </div>
      <div class="user-menu-item" @click="handleSettings">
        <el-icon><Setting /></el-icon>
        <span>设置</span>
      </div>
      <div class="user-menu-divider"></div>
      <div class="user-menu-item user-menu-item--danger" @click="handleLogoutClick">
        <el-icon><SwitchButton /></el-icon>
        <span>退出登录</span>
      </div>
      <div class="user-menu-divider"></div>
      <div class="user-menu-item user-menu-item--danger" @click="handleDeleteAccount">
        <el-icon><WarningFilled /></el-icon>
        <span>注销账号</span>
      </div>
    </div>
  </Teleport>

  <el-dialog v-model="editDialogVisible" title="编辑个人资料" width="720px" :close-on-click-modal="false" destroy-on-close @closed="handleEditDialogClosed">
    <div class="edit-avatar-section">
      <label class="edit-avatar-upload-area">
        <input type="file" accept="image/*" class="edit-avatar-input" @change="handleAvatarFileChange" />
        <div class="edit-avatar-wrapper">
          <el-avatar :size="160" :src="avatarPreview || undefined" icon="UserFilled" class="edit-avatar-img" />
          <div class="edit-avatar-camera-badge">
            <el-icon :size="16"><Camera /></el-icon>
          </div>
        </div>
      </label>
    </div>
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
    <p class="edit-form-tip">你的个人资料有助于大家认出你。</p>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="editLoading" @click="handleSaveProfile">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="cropDialogVisible" title="裁剪头像" width="520px" :close-on-click-modal="false" destroy-on-close @opened="onCropDialogOpened" @closed="onCropDialogClosed">
    <div class="crop-dialog-body">
      <div ref="croppieRef" class="crop-area"></div>
    </div>
    <template #footer>
      <el-button @click="cancelCrop">取消</el-button>
      <el-button type="primary" :loading="cropLoading" @click="confirmCrop">确认裁剪</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="settingsDialogVisible" width="680px" :close-on-click-modal="false" destroy-on-close :show-close="true" class="settings-dialog" @open="handleSettingsOpen">
    <template #header>
      <span></span>
    </template>
    <div class="settings-layout">
      <div class="settings-nav">
        <div
          v-for="item in settingsNavItems"
          :key="item.key"
          class="settings-nav-item"
          :class="{ active: activeSettingsNav === item.key }"
          @click="activeSettingsNav = item.key"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>
      <div class="settings-content">
        <div class="settings-section-title">{{ currentSettingsLabel }}</div>
        <div v-if="activeSettingsNav === 'voice'" class="settings-voice">
          <div class="settings-voice-item">
            <div class="settings-voice-item-info">
              <span class="settings-voice-item-label">语音播放</span>
              <span class="settings-voice-item-desc">开启后，大模型输出内容时将自动语音播报</span>
            </div>
            <el-switch v-model="voiceEnabled" @change="handleVoiceEnabledChange" />
          </div>
          <div class="settings-voice-item">
            <div class="settings-voice-item-info">
              <span class="settings-voice-item-label">音色选择</span>
              <span class="settings-voice-item-desc">选择语音播报的音色</span>
            </div>
            <el-select v-model="voiceType" placeholder="请选择音色" size="default" class="settings-voice-select" popper-class="settings-voice-popper" @change="handleVoiceTypeChange">
              <el-option v-for="v in voiceOptions" :key="v.value" :label="v.label" :value="v.value" />
            </el-select>
          </div>
          <div class="settings-voice-item">
            <div class="settings-voice-item-info">
              <span class="settings-voice-item-label">音量调节</span>
              <span class="settings-voice-item-desc">调节语音播报的音量大小</span>
            </div>
            <div class="settings-voice-volume">
              <el-slider v-model="voiceVolume" :min="0" :max="100" :step="1" size="small" class="settings-voice-slider" @input="handleVoiceVolumeChange" />
              <span class="settings-voice-volume-value">{{ voiceVolume }}</span>
            </div>
          </div>
        </div>

        <div v-if="activeSettingsNav === 'theme'" class="settings-theme">
          <div class="settings-theme-desc">选择界面主题外观</div>
          <el-radio-group v-model="themeMode" class="settings-theme-group" @change="handleThemeChange">
            <el-radio-button value="light">Light</el-radio-button>
            <el-radio-button value="dark">Dark</el-radio-button>
          </el-radio-group>
        </div>

        <div v-if="activeSettingsNav === 'personalization'" class="settings-personalization">
          <div class="settings-personalization-desc">在基本风格和语调的基础上选择额外的自定义项</div>
          <div v-for="item in personalizationItems" :key="item.key" class="settings-personalization-item">
            <div class="settings-personalization-item-header">
              <span class="settings-personalization-item-label">{{ item.label }}</span>
              <el-select
                :model-value="personalizationValues[item.key] ?? 0"
                placeholder="默认"
                size="default"
                class="settings-personalization-select"
                popper-class="settings-personalization-popper"
                @change="(val: number) => handlePersonalizationChange(item.key, val)"
              >
                <el-option :value="-1" label="减弱">
                  <div class="personalization-option-label">减弱</div>
                  <div class="personalization-option-desc">{{ item.descWeaken }}</div>
                </el-option>
                <el-option :value="0" label="默认">
                  <div class="personalization-option-label">默认</div>
                </el-option>
                <el-option :value="1" label="增强">
                  <div class="personalization-option-label">增强</div>
                  <div class="personalization-option-desc">{{ item.descEnhance }}</div>
                </el-option>
              </el-select>
            </div>
          </div>
        </div>
      </div>
    </div>
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
          <el-tooltip
            :content="sess.title"
            placement="top"
            :show-after="500"
            :disabled="sess.title.length < 15"
          >
            <div class="search-result-title">{{ sess.title }}</div>
          </el-tooltip>
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
import { SwitchButton, Edit, ArrowRight, Delete, ChatDotRound, FolderOpened, MoreFilled, Search, Setting, User, Camera, Headset, Sunny, MagicStick, OfficeBuilding, Promotion, WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/store/modules/auth'
import { ElMessageBox, ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getSessionsApi, deleteSessionApi, updateSessionTitleApi, togglePinSessionApi } from '@/api/chat'
import type { SessionInfo } from '@/types'
import { useSettings } from '@/composables/layout/useSettings'

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
const settingsDialogVisible = ref(false)
const sessions = ref<SessionInfo[]>([])
const searchDialogVisible = ref(false)
const searchKeyword = ref('')
const searchInputRef = ref<any>()

const {
  settingsNavItems,
  personalizationItems,
  activeSettingsNav,
  voiceEnabled,
  voiceOptions,
  voiceType,
  voiceVolume,
  themeMode,
  personalizationValues,
  croppieRef,
  croppieVisible,
  cropDialogVisible,
  cropLoading,
  avatarPreview,
  loadPersonalizationValues,
  handlePersonalizationChange,
  applyTheme,
  handleThemeChange,
  handleVoiceEnabledChange,
  handleVoiceTypeChange,
  handleVoiceVolumeChange,
  onSettingsOpen,
  handleAvatarFileChange,
  onCropDialogOpened,
  onCropDialogClosed,
  cancelCrop,
  confirmCrop,
  resetCroppie,
  destroyCroppie,
} = useSettings(() => authStore.user?.id)

const activeSessionId = computed(() => {
  return (route.params.sessionId as string) || (route.query.sessionId as string) || null
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

const isPlazaRoute = computed(() => {
  return route.path.startsWith('/plaza')
})

const isOrganizationsRoute = computed(() => {
  return route.path.startsWith('/organizations')
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

function handleUserAreaClick() {
  if (!authStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: '/chat' } })
    return
  }
  toggleUserMenu()
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

async function handleDeleteAccount() {
  popoverVisible.value = false

  // 第一次确认：是否确认要执行注销操作
  try {
    await ElMessageBox.confirm(
      '是否确认要执行注销操作？',
      '注销账号',
      {
        confirmButtonText: '确认注销',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
        customClass: 'delete-account-dialog'
      }
    )
  } catch {
    return
  }

  // 第二次确认：提示注销后该账号会消失
  try {
    await ElMessageBox.confirm(
      '注销后该账号会消失，知识库、文档、对话记录等所有数据将被永久删除且无法恢复。',
      '最后确认',
      {
        confirmButtonText: '确认注销',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
        customClass: 'delete-account-dialog'
      }
    )
  } catch {
    return
  }

  // 密码验证
  try {
    const { value } = await ElMessageBox.prompt('请输入当前密码以确认注销', '安全验证', {
      confirmButtonText: '确认注销',
      cancelButtonText: '取消',
      inputType: 'password',
      inputValidator: (val: string) => {
        if (!val) return '请输入密码'
        if (val.length < 6) return '密码长度至少6位'
        return true
      }
    })
    await authStore.deleteAccount(value)
    ElMessage.success('账号已注销')
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
  avatarPreview.value = user?.avatar || null
  croppieVisible.value = false
  editDialogVisible.value = true
}

const currentSettingsLabel = computed(() => {
  const item = settingsNavItems.find(i => i.key === activeSettingsNav.value)
  return item?.label || ''
})

function handleSettings() {
  popoverVisible.value = false
  activeSettingsNav.value = settingsNavItems[0]?.key || 'voice'
  settingsDialogVisible.value = true
}

function handleSettingsOpen() {
  onSettingsOpen()
}

function handleEditDialogClosed() {
  resetCroppie()
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
      phone: editForm.phone || null,
      avatar: avatarPreview.value || null
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
  if (!authStore.isAuthenticated) return
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
  if (!authStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: '/documents' } })
    return
  }
  router.push('/documents')
}

function handleNavToPlaza() {
  if (!authStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: '/plaza' } })
    return
  }
  router.push('/plaza')
}

function handleNavToOrganizations() {
  if (!authStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: '/organizations' } })
    return
  }
  router.push('/organizations')
}

function handleSearchConversations() {
  if (!authStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: '/chat' } })
    return
  }
  searchDialogVisible.value = true
}

function handleSelectSession(sessionId: string) {
  const sess = sessions.value.find(s => s.id === sessionId)
  if (sess?.knowledge_base_id) {
    router.push(`/plaza/${sess.knowledge_base_id}/chat?sessionId=${sessionId}`)
  } else {
    router.push(`/chat/${sessionId}`)
  }
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
    const sess = sessions.value.find(s => s.id === sessionId)
    await deleteSessionApi(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (activeSessionId.value === sessionId) {
      if (sess?.knowledge_base_id) {
        router.push(`/plaza/${sess.knowledge_base_id}/chat`)
      } else {
        router.push('/chat')
      }
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
      closeOnClickModal: false
    } as any)
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
  loadPersonalizationValues()
  applyTheme(themeMode.value)
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  destroyCroppie()
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

.edit-avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
}

.edit-avatar-upload-area {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.edit-avatar-wrapper {
  position: relative;
  display: inline-block;
}

.edit-avatar-img {
  flex-shrink: 0;
}

.edit-avatar-img :deep(.el-icon) {
  font-size: 64px;
}

.edit-avatar-camera-badge {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  border: 2px solid #fff;
}

.edit-avatar-input {
  display: none;
}

.edit-avatar-cancel-row {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.crop-dialog-body {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 380px;
  padding-bottom: 20px;
}

.crop-dialog-body .crop-area {
  width: 300px;
  height: 300px;
  touch-action: none;
  pointer-events: auto;
  user-select: none;
  -webkit-user-select: none;
}

.crop-dialog-body .crop-area .cr-viewport {
  cursor: move;
  pointer-events: auto;
  overflow: hidden;
}

.crop-dialog-body .crop-area .cr-image {
  pointer-events: auto;
  cursor: move;
  max-width: none;
  position: absolute;
}

.crop-dialog-body .crop-area .cr-slider-wrap {
  margin-top: 10px;
  padding: 0 10px;
}

.edit-avatar-crop-actions {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.edit-form-tip {
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 16px;
}

.settings-body {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}

.settings-layout {
  display: flex;
  min-height: 280px;
}

.settings-nav {
  width: 160px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  padding: 8px 0;
}

.settings-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin: 0 8px 2px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-main);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.settings-nav-item:hover {
  background: var(--gradient-subtle);
  color: var(--color-primary);
}

.settings-nav-item.active {
  background: var(--gradient-subtle);
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.settings-content {
  flex: 1;
  padding: 0 8px 0 24px;
}

.settings-section-title {
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin-bottom: 24px;
}

.settings-voice-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
}

.settings-voice-item + .settings-voice-item {
  border-top: 1px solid var(--color-border-light);
}

.settings-voice-item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.settings-voice-item-label {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
}

.settings-voice-item-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.settings-voice-select {
  width: 180px;
}

.settings-voice-volume {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settings-voice-slider {
  width: 180px;
}

.settings-voice-volume-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  min-width: 32px;
  text-align: right;
}

.settings-theme-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 20px;
}

.settings-theme-group {
  display: flex;
  gap: 12px;
}

.settings-personalization-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 20px;
  line-height: 1.6;
}

.settings-personalization-item {
  padding: 14px 0;
}

.settings-personalization-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.settings-personalization-item-label {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
}

.settings-personalization-select {
  width: 140px;
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

/* ── Settings Dialog Overrides ──────────────────────── */
.settings-dialog {
  --el-color-primary: var(--color-primary);
  --el-color-primary-light-3: var(--color-primary);
  --el-color-primary-light-5: var(--color-primary);
  --el-color-primary-light-7: #C7D2FE;
  --el-color-primary-light-8: #E0E7FF;
  --el-color-primary-light-9: #EEF2FF;
  --el-fill-color-light: var(--gradient-subtle);
}

.settings-dialog .el-switch.is-checked .el-switch__core {
  background: var(--color-primary) !important;
  border-color: var(--color-primary) !important;
}

.settings-dialog .el-select .el-input__wrapper {
  box-shadow: 0 0 0 1px var(--color-border) inset !important;
}

.settings-dialog .el-select .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--color-primary) inset !important;
}

.settings-dialog .el-select .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 1px var(--color-primary) inset !important;
}

.settings-voice-popper {
  --el-color-primary: var(--color-primary);
  --el-color-primary-light-3: var(--color-primary);
  --el-color-primary-light-5: var(--color-primary);
  --el-color-primary-light-7: #C7D2FE;
  --el-color-primary-light-8: #E0E7FF;
  --el-color-primary-light-9: #EEF2FF;
  --el-fill-color-light: var(--gradient-subtle);
  background: var(--color-surface) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: var(--shadow-card-hover) !important;
  border: 1px solid var(--color-border-light) !important;
}

.settings-voice-popper .el-select-dropdown__item {
  color: var(--color-text-main);
  font-weight: var(--font-weight-medium);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.settings-voice-popper .el-select-dropdown__item:hover {
  background: var(--gradient-subtle) !important;
  color: var(--color-primary) !important;
}

.settings-voice-popper .el-select-dropdown__item.is-selected {
  color: var(--color-primary) !important;
  background: var(--gradient-subtle) !important;
  font-weight: var(--font-weight-semibold) !important;
}

.settings-personalization-popper {
  --el-color-primary: var(--color-primary);
  --el-color-primary-light-3: var(--color-primary);
  --el-color-primary-light-5: var(--color-primary);
  --el-color-primary-light-7: #C7D2FE;
  --el-color-primary-light-8: #E0E7FF;
  --el-color-primary-light-9: #EEF2FF;
  --el-fill-color-light: var(--gradient-subtle);
  background: var(--color-surface) !important;
  border-radius: var(--radius-sm) !important;
  box-shadow: var(--shadow-card-hover) !important;
  border: 1px solid var(--color-border-light) !important;
}

.settings-personalization-popper .el-select-dropdown__item {
  color: var(--color-text-main);
  font-weight: var(--font-weight-medium);
  transition: background var(--transition-fast), color var(--transition-fast);
  height: auto;
  padding: 8px 16px;
  line-height: 1.5;
}

.settings-personalization-popper .el-select-dropdown__item:hover {
  background: var(--gradient-subtle) !important;
  color: var(--color-primary) !important;
}

.settings-personalization-popper .el-select-dropdown__item.is-selected {
  color: var(--color-primary) !important;
  background: var(--gradient-subtle) !important;
  font-weight: var(--font-weight-semibold) !important;
}

.personalization-option-label {
  font-size: var(--font-size-base);
  color: inherit;
}

.personalization-option-desc {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.settings-theme-group .el-radio-button__inner {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--color-border) !important;
}

.settings-theme-group .el-radio-button:first-child .el-radio-button__inner {
  border-radius: var(--radius-sm) !important;
}

.settings-theme-group .el-radio-button:last-child .el-radio-button__inner {
  border-radius: var(--radius-sm) !important;
}

.settings-theme-group .el-radio-button.is-active .el-radio-button__inner {
  background: var(--gradient-primary) !important;
  border-color: var(--color-primary) !important;
  color: #fff !important;
  box-shadow: var(--shadow-button) !important;
}

/* ── 注销确认弹窗 ────────────────────────────────── */
.delete-account-dialog {
  --el-messagebox-width: 480px;
}
</style>
