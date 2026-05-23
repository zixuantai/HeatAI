<template>
  <div class="org-page">
    <div class="org-sidebar">
      <div class="org-sidebar-spacer"></div>

      <div class="org-avatar-section">
        <div v-if="selectedOrg?.avatar" class="org-main-avatar-wrapper" :style="isGradient(selectedOrg.avatar) ? { background: selectedOrg.avatar } : {}">
          <img v-if="!isGradient(selectedOrg.avatar)" :src="selectedOrg.avatar" class="org-main-avatar-img" alt="组织头像" />
          <el-icon v-else :size="48" color="#fff"><OfficeBuilding /></el-icon>
        </div>
        <div v-else class="org-avatar-empty">
          <el-icon :size="48"><OfficeBuilding /></el-icon>
        </div>
      </div>

      <div class="org-info-section" v-if="selectedOrg">
        <h2 class="org-info-name">{{ selectedOrg.name }}</h2>
        <p class="org-info-desc">{{ selectedOrg.description || '暂无描述' }}</p>
        <div class="org-info-meta">
          <div class="org-meta-item">
            <el-icon><User /></el-icon>
            <span>成员数: {{ selectedOrg.member_count || 0 }}</span>
          </div>
          <div class="org-meta-item">
            <el-icon><Key /></el-icon>
            <span>邀请码: {{ showInviteCode ? selectedOrg.invite_code : '••••••••' }}</span>
            <el-icon class="org-eye-btn" @click="showInviteCode = !showInviteCode">
              <component :is="showInviteCode ? View : Hide" />
            </el-icon>
            <el-tooltip content="复制邀请码" placement="top">
              <el-icon class="org-copy-btn" @click="handleCopyInviteCode(selectedOrg)"><CopyDocument /></el-icon>
            </el-tooltip>
          </div>
          <div class="org-meta-item">
            <el-icon><Calendar /></el-icon>
            <span>创建时间: {{ formatDate(selectedOrg.created_at) }}</span>
          </div>
        </div>
      </div>

      <div class="org-info-section org-info-empty" v-else>
        <p class="org-empty-text">暂无组织信息</p>
        <p class="org-empty-hint">请从右侧列表选择或创建一个组织</p>
      </div>

      <div class="org-actions">
        <template v-if="authStore.isAdmin">
          <div 
            class="org-action-card" 
            :class="{ 'org-action-card-disabled': organizations.length === 0 }"
            @click="organizations.length > 0 && (activeView = 'manage')"
          >
            <div class="org-action-card-icon org-action-card-icon-manage">
              <el-icon :size="24"><Setting /></el-icon>
            </div>
            <div class="org-action-card-content">
              <span class="org-action-card-title">管理我的组织</span>
              <span class="org-action-card-hint">{{ organizations.length > 0 ? '查看和管理已加入的组织' : '暂无组织可管理' }}</span>
            </div>
          </div>
          <div 
            class="org-action-card"
            :class="{ 'org-action-card-disabled': hasCreatedOrg }"
            @click="!hasCreatedOrg && (showCreateDialog = true)"
          >
            <div class="org-action-card-icon org-action-card-icon-create">
              <el-icon :size="24"><Plus /></el-icon>
            </div>
            <div class="org-action-card-content">
              <span class="org-action-card-title">创建新组织</span>
              <span class="org-action-card-hint">{{ hasCreatedOrg ? '您已创建过组织' : '点击创建并管理团队' }}</span>
            </div>
          </div>
        </template>
        <template v-else>
          <div 
            class="org-action-card" 
            :class="{ 'org-action-card-disabled': organizations.length === 0 }"
            @click="organizations.length > 0 && (activeView = 'manage')"
          >
            <div class="org-action-card-icon org-action-card-icon-view">
              <el-icon :size="24"><View /></el-icon>
            </div>
            <div class="org-action-card-content">
              <span class="org-action-card-title">查看组织</span>
              <span class="org-action-card-hint">{{ organizations.length > 0 ? '查看已加入的组织' : '暂未加入任何组织' }}</span>
            </div>
          </div>
          <div 
            class="org-action-card"
            :class="{ 'org-action-card-disabled': hasJoinedOrg }"
            @click="!hasJoinedOrg && (showJoinDialog = true)"
          >
            <div class="org-action-card-icon org-action-card-icon-join">
              <el-icon :size="24"><CirclePlusFilled /></el-icon>
            </div>
            <div class="org-action-card-content">
              <span class="org-action-card-title">加入组织</span>
              <span class="org-action-card-hint">{{ hasJoinedOrg ? '您已加入组织' : '输入邀请码加入团队' }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="org-main">
      <template v-if="activeView === 'list'">
        <div class="org-search-bar">
          <el-input
            v-model="searchQuery"
            placeholder="搜索组织..."
            clearable
            size="large"
            class="org-search-input"
            @input="handleSearch"
            @clear="handleClearSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <span class="org-count">共 {{ filteredOrganizations.length }} 个组织</span>
        </div>

        <div class="org-list" v-loading="loading">
          <div
            v-for="org in filteredOrganizations"
            :key="org.id"
            class="org-card"
            :class="{ 'org-card-active': authStore.currentOrgId === org.id }"
            @click="handleSelectOrg(org)"
          >
            <div class="org-card-left">
              <div v-if="org.avatar" class="org-card-avatar-wrapper" :style="isGradient(org.avatar) ? { background: org.avatar } : {}">
                <img v-if="!isGradient(org.avatar)" :src="org.avatar" class="org-card-avatar-img" alt="组织头像" />
                <el-icon v-else :size="24" color="#fff"><OfficeBuilding /></el-icon>
              </div>
              <div v-else class="org-card-avatar-placeholder" :style="{ background: getCoverColor(org.name) }">
                {{ org.name.charAt(0) }}
              </div>
            </div>

            <div class="org-card-body">
              <div class="org-card-header">
                <h3 class="org-card-title">{{ org.name }}</h3>
                <el-tag v-if="authStore.currentOrgId === org.id" type="success" size="small" effect="dark">当前</el-tag>
              </div>
              <p class="org-card-desc">{{ org.description || '暂无描述' }}</p>
              <div class="org-card-footer">
                <span class="org-card-date">{{ formatDate(org.created_at) }}</span>
                <div class="org-card-actions">
                  <el-tooltip content="复制邀请码" placement="top" :show-after="300">
                    <button class="org-action-btn" @click.stop="handleCopyInviteCode(org)">
                      <el-icon :size="14"><CopyDocument /></el-icon>
                    </button>
                  </el-tooltip>
                  <el-tooltip v-if="authStore.currentOrgId !== org.id" content="切换到此组织" placement="top" :show-after="300">
                    <button class="org-action-btn org-action-btn-primary" @click.stop="handleSelectOrg(org)">
                      <el-icon :size="14"><Switch /></el-icon>
                    </button>
                  </el-tooltip>
                </div>
              </div>
            </div>
          </div>

          <el-empty
            v-if="!loading && filteredOrganizations.length === 0"
            description="暂无组织"
            class="org-list-empty"
          />
        </div>
      </template>

      <template v-else-if="activeView === 'manage'">
        <div class="org-manage-header">
          <el-button :icon="ArrowLeft" @click="activeView = 'list'">返回组织列表</el-button>
          <h2 class="org-manage-title">管理我的组织</h2>
        </div>
        <div class="org-manage-content">
          <el-empty description="管理功能开发中..." />
        </div>
      </template>
    </div>

    <el-dialog
      v-model="showCreateDialog"
      title="创建组织"
      width="520px"
      :close-on-click-modal="false"
      class="org-dialog"
    >
      <div class="org-dialog-content">
        <div class="org-avatar-section-dialog">
          <div class="org-avatar-upload" @click="triggerAvatarUpload">
            <input
              ref="avatarInputRef"
              type="file"
              accept="image/*"
              style="display: none"
              @change="handleAvatarChange"
            />
            <el-avatar
              v-if="createForm.avatarPreview && !createForm.selectedDefault"
              :src="createForm.avatarPreview"
              :size="72"
              shape="square"
              class="org-avatar-preview"
            />
            <div v-else-if="createForm.selectedDefault" class="org-default-avatar-preview" :style="{ background: defaultAvatars[createForm.selectedDefault].bg }">
              <el-icon :size="28"><component :is="defaultAvatars[createForm.selectedDefault].icon" /></el-icon>
            </div>
            <div v-else class="org-avatar-placeholder">
              <el-icon :size="24"><Camera /></el-icon>
              <span>自定义</span>
            </div>
          </div>
        </div>

        <div class="org-default-avatars">
          <span class="org-default-avatars-label">选择默认头像</span>
          <div class="org-default-avatars-grid">
            <div
              v-for="(avatar, key) in defaultAvatars"
              :key="key"
              class="org-default-avatar-item"
              :class="{ 'org-default-avatar-active': createForm.selectedDefault === key }"
              :style="{ background: avatar.bg }"
              @click="handleSelectDefaultAvatar(key)"
            >
              <el-icon :size="20" color="#fff"><component :is="avatar.icon" /></el-icon>
            </div>
          </div>
        </div>

        <el-form :model="createForm" label-position="top" class="org-form">
          <el-form-item label="组织名称" required>
            <el-input
              v-model="createForm.name"
              placeholder="请输入组织名称"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="组织描述">
            <el-input
              v-model="createForm.description"
              type="textarea"
              :rows="3"
              placeholder="请输入组织描述（可选）"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
          <div class="org-form-contact">
            <el-form-item label="联系电话" class="org-form-contact-item">
              <el-input
                v-model="createForm.phone"
                placeholder="请输入联系电话"
                maxlength="20"
              />
            </el-form-item>
            <el-form-item label="联系邮箱" class="org-form-contact-item">
              <el-input
                v-model="createForm.email"
                placeholder="请输入联系邮箱"
                maxlength="100"
              />
            </el-form-item>
          </div>
          <div class="org-import-row">
            <el-button
              type="primary"
              link
              size="small"
              class="org-import-btn"
              @click="handleImportFromProfile"
            >
              从个人信息导入
            </el-button>
          </div>
        </el-form>
      </div>
      <template #footer>
        <div class="org-dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" :loading="createLoading" @click="handleCreate">
            创建
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showJoinDialog"
      title="加入组织"
      width="420px"
      :close-on-click-modal="false"
      class="org-dialog"
    >
      <div class="org-dialog-content">
        <div class="org-join-icon">
          <el-icon :size="48"><Connection /></el-icon>
        </div>
        <p class="org-join-hint">请输入管理员提供的邀请码加入组织</p>
        <el-form :model="joinForm" label-position="top" class="org-form">
          <el-form-item label="邀请码" required>
            <el-input
              v-model="joinForm.code"
              placeholder="请输入邀请码"
              maxlength="20"
            >
              <template #prefix>
                <el-icon><Key /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="org-dialog-footer">
          <el-button @click="showJoinDialog = false">取消</el-button>
          <el-button type="primary" :loading="joinLoading" @click="handleJoin">
            加入
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Search, Plus, Key, CopyDocument, Switch, Camera, Calendar, OfficeBuilding, Setting, ArrowLeft, User, View, Hide, CirclePlusFilled, Connection
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/modules/auth'
import { createOrganizationApi, joinByInviteCodeApi } from '@/api/organizations'
import type { Organization } from '@/types'

const authStore = useAuthStore()
const loading = ref(false)
const searchQuery = ref('')
const showCreateDialog = ref(false)
const showJoinDialog = ref(false)
const createLoading = ref(false)
const joinLoading = ref(false)
const avatarInputRef = ref<HTMLInputElement | null>(null)
const activeView = ref<'list' | 'manage'>('list')
const showInviteCode = ref(false)

const joinForm = ref({
  code: ''
})

const hasCreatedOrg = computed(() => {
  return organizations.value.some(org => org.created_by === authStore.user?.id)
})

const hasJoinedOrg = computed(() => {
  return organizations.value.length > 0
})

const createForm = ref({
  name: '',
  description: '',
  avatar: '',
  avatarPreview: '',
  selectedDefault: '' as string,
  phone: '',
  email: ''
})

const defaultAvatars: Record<string, { bg: string; icon: any }> = {
  purple: { bg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', icon: OfficeBuilding },
  pink: { bg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', icon: OfficeBuilding },
  blue: { bg: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', icon: OfficeBuilding },
  green: { bg: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', icon: OfficeBuilding },
  orange: { bg: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', icon: OfficeBuilding },
  lavender: { bg: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', icon: OfficeBuilding },
  gold: { bg: 'linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)', icon: OfficeBuilding },
  cyan: { bg: 'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)', icon: OfficeBuilding }
}

const organizations = computed(() => authStore.organizations)

const selectedOrg = computed(() => {
  if (!authStore.currentOrgId) return organizations.value[0] || null
  return organizations.value.find(o => o.id === authStore.currentOrgId) || organizations.value[0] || null
})

const filteredOrganizations = computed(() => {
  if (!searchQuery.value.trim()) return organizations.value
  const query = searchQuery.value.trim().toLowerCase()
  return organizations.value.filter(
    org => org.name.toLowerCase().includes(query) ||
           (org.description && org.description.toLowerCase().includes(query))
  )
})

const coverColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
  'linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)',
  'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)',
]

function getCoverColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return coverColors[Math.abs(hash) % coverColors.length]
}

function isGradient(avatar: string): boolean {
  return avatar.startsWith('linear-gradient')
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function handleSearch() {}

function handleClearSearch() {
  searchQuery.value = ''
}

function triggerAvatarUpload() {
  avatarInputRef.value?.click()
}

function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('头像文件大小不能超过 2MB')
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    const base64 = e.target?.result as string
    createForm.value.avatar = base64
    createForm.value.avatarPreview = base64
    createForm.value.selectedDefault = ''
  }
  reader.readAsDataURL(file)
  input.value = ''
}

function handleSelectDefaultAvatar(key: string) {
  createForm.value.selectedDefault = key
  createForm.value.avatar = defaultAvatars[key].bg
  createForm.value.avatarPreview = ''
}

function handleImportFromProfile() {
  const user = authStore.user
  if (!user) {
    ElMessage.warning('请先登录')
    return
  }

  if (!user.phone && !user.email) {
    ElMessage.warning('请完善个人信息')
    return
  }

  if (user.phone) {
    createForm.value.phone = user.phone
  }
  if (user.email) {
    createForm.value.email = user.email
  }
  ElMessage.success('已导入个人信息')
}

async function handleCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入组织名称')
    return
  }

  createLoading.value = true
  try {
    await createOrganizationApi({
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim() || undefined,
      avatar: createForm.value.avatar || undefined,
      phone: createForm.value.phone.trim() || undefined,
      email: createForm.value.email.trim() || undefined
    })
    ElMessage.success('组织创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '', avatar: '', avatarPreview: '', selectedDefault: '', phone: '', email: '' }
    await authStore.fetchOrganizations()
  } catch (error: any) {
    ElMessage.error(error?.message || '创建失败')
  } finally {
    createLoading.value = false
  }
}

async function handleJoin() {
  if (!joinForm.value.code.trim()) {
    ElMessage.warning('请输入邀请码')
    return
  }

  joinLoading.value = true
  try {
    await joinByInviteCodeApi({ code: joinForm.value.code.trim() })
    ElMessage.success('加入组织成功')
    showJoinDialog.value = false
    joinForm.value = { code: '' }
    await authStore.fetchOrganizations()
  } catch (error: any) {
    ElMessage.error(error?.message || '加入失败')
  } finally {
    joinLoading.value = false
  }
}

function handleSelectOrg(org: Organization) {
  if (authStore.currentOrgId === org.id) {
    authStore.setCurrentOrg(null)
    ElMessage.info('已退出当前组织')
  } else {
    authStore.setCurrentOrg(org.id)
    ElMessage.success(`已切换到组织: ${org.name}`)
  }
}

function handleCopyInviteCode(org: Organization) {
  navigator.clipboard.writeText(org.invite_code).then(() => {
    ElMessage.success('邀请码已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}

onMounted(async () => {
  loading.value = true
  try {
    await authStore.fetchOrganizations()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.org-page {
  display: flex;
  height: 100vh;
  background: var(--color-bg);
  overflow: hidden;
}

.org-sidebar {
  width: 320px;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  padding: 24px;
  flex-shrink: 0;
}

.org-sidebar-spacer {
  flex: 0.3;
}

.org-avatar-section {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.org-main-avatar-wrapper {
  width: 120px;
  height: 120px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.org-main-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.org-avatar-empty {
  width: 120px;
  height: 120px;
  border-radius: var(--radius-lg);
  background: var(--color-bg);
  border: 2px dashed var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.org-info-section {
  flex: 1;
  margin-bottom: 24px;
}

.org-info-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  text-align: center;
  padding-top: 8px;
}

.org-empty-text {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  margin: 0 0 8px;
}

.org-empty-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.org-info-name {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin: 0 0 12px;
  text-align: center;
}

.org-info-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 20px;
  line-height: var(--leading-relaxed);
  text-align: center;
}

.org-info-meta {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
}

.org-meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.org-eye-btn {
  cursor: pointer;
  color: var(--color-text-muted);
  transition: color 0.2s ease;
}

.org-eye-btn:hover {
  color: var(--color-primary);
}

.org-copy-btn {
  margin-left: 4px;
  cursor: pointer;
  color: var(--color-primary);
  transition: transform 0.2s ease;
}

.org-copy-btn:hover {
  transform: scale(1.2);
}

.org-actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.org-action-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--color-bg);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.25s ease;
}

.org-action-card:hover {
  border-color: var(--color-primary);
  background: rgba(79, 70, 229, 0.03);
}

.org-action-card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.org-action-card-icon-manage {
  background: var(--gradient-primary);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.org-action-card-icon-create {
  background: var(--gradient-primary);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.org-action-card-icon-join {
  background: var(--gradient-primary);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.org-action-card-icon-view {
  background: var(--gradient-primary);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.org-action-card:hover .org-action-card-icon {
  transform: scale(1.05);
}

.org-action-card-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.org-action-card-disabled:hover {
  border-color: var(--color-border);
  background: var(--color-bg);
}

.org-action-card-disabled:hover .org-action-card-icon {
  transform: none;
}

.org-action-card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.org-action-card-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
}

.org-action-card-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.org-manage-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 32px;
}

.org-manage-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin: 0;
}

.org-manage-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.org-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.org-search-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px 32px 24px;
}

.org-search-input {
  flex: 1;
  max-width: 600px;
}

.org-search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-full) !important;
  box-shadow: none !important;
  border: 1px solid var(--color-border) !important;
  background: transparent !important;
  padding: 0 20px;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.org-search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary) !important;
}

.org-search-input :deep(.el-input.is-focus .el-input__wrapper) {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important;
  background: rgba(79, 70, 229, 0.03) !important;
}

.org-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.org-list {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.org-list-empty {
  margin-top: 80px;
}

.org-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  padding: 20px 24px;
  cursor: pointer;
  box-shadow: var(--neu-card);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.org-card:hover {
  transform: translateX(4px);
  box-shadow: var(--neu-card-hover);
  border-color: var(--color-primary);
}

.org-card-active {
  border-color: var(--color-primary);
  box-shadow: var(--neu-card), 0 0 0 2px rgba(79, 70, 229, 0.15);
}

.org-card-left {
  flex-shrink: 0;
}

.org-card-avatar-wrapper {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.org-card-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.org-card-avatar-placeholder {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: var(--font-weight-bold);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.org-card-body {
  flex: 1;
  min-width: 0;
}

.org-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.org-card-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.org-card-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.org-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.org-card-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.org-card-actions {
  display: flex;
  gap: 8px;
}

.org-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 150ms ease;
  font-family: var(--font-family);
}

.org-action-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

.org-action-btn-primary {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.org-action-btn-primary:hover {
  background: var(--color-primary);
  color: #fff;
}

.org-dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 10px 0;
}

.org-avatar-section-dialog {
  display: flex;
  justify-content: center;
}

.org-avatar-upload {
  width: 88px;
  height: 88px;
  border-radius: var(--radius-lg);
  border: 2px dashed var(--color-border);
  cursor: pointer;
  overflow: hidden;
  transition: border-color var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.org-avatar-upload:hover {
  border-color: var(--color-primary);
}

.org-avatar-preview {
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg) !important;
}

.org-default-avatar-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.org-avatar-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.org-default-avatars {
  width: 100%;
}

.org-default-avatars-label {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin-bottom: 12px;
  text-align: center;
}

.org-default-avatars-grid {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.org-default-avatar-item {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 3px solid transparent;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.org-default-avatar-item:hover {
  transform: scale(1.1);
}

.org-default-avatar-active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.3), 0 4px 12px rgba(0, 0, 0, 0.15);
}

.org-form {
  width: 100%;
}

.org-join-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.3);
}

.org-join-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  text-align: center;
  margin: 0;
}

.org-form-contact {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-start;
}

.org-form-contact-item {
  flex: 1;
  min-width: 140px;
}

.org-import-row {
  display: flex;
  justify-content: flex-end;
  margin-top: -10px;
  margin-bottom: 8px;
}

.org-import-btn {
  font-size: var(--font-size-xs);
  color: var(--color-primary) !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0;
  height: auto;
}

.org-import-btn:hover {
  color: var(--color-primary) !important;
  opacity: 0.8;
}

.org-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1024px) {
  .org-page {
    flex-direction: column;
  }

  .org-sidebar {
    width: 100%;
    flex-direction: row;
    align-items: center;
    gap: 24px;
    padding: 20px 24px;
    border-right: none;
    border-bottom: 1px solid var(--color-border-light);
  }

  .org-avatar-section {
    margin-bottom: 0;
  }

  .org-info-section {
    flex: 1;
    margin-bottom: 0;
    text-align: left;
  }

  .org-info-name {
    text-align: left;
  }

  .org-info-desc {
    text-align: left;
  }

  .org-actions {
    margin-top: 0;
    margin-left: auto;
  }

  .org-create-btn {
    width: auto;
  }
}

@media (max-width: 768px) {
  .org-sidebar {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  .org-info-section {
    text-align: center;
  }

  .org-info-name {
    text-align: center;
  }

  .org-info-desc {
    text-align: center;
  }

  .org-actions {
    margin-left: 0;
    width: 100%;
  }

  .org-create-btn {
    width: 100%;
  }

  .org-search-bar {
    padding: 16px;
    flex-direction: column;
    gap: 12px;
  }

  .org-search-input {
    max-width: 100%;
  }

  .org-list {
    padding: 16px;
  }
}
</style>
