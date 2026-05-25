<template>
  <div class="org-page">
    <div class="org-sidebar" :class="{ collapsed }">
      <div class="org-sidebar-header">
        <div v-show="!collapsed" class="org-sidebar-spacer"></div>
        <div class="org-sidebar-toggle" @click="collapsed = !collapsed">
          <el-icon :size="18">
            <component :is="collapsed ? ArrowRight : ArrowLeft" />
          </el-icon>
        </div>
      </div>

      <div v-show="!collapsed" class="org-avatar-section">
        <div v-if="selectedOrg?.avatar" class="org-main-avatar-wrapper" :style="isGradient(selectedOrg.avatar) ? { background: selectedOrg.avatar } : {}">
          <img v-if="!isGradient(selectedOrg.avatar)" :src="selectedOrg.avatar" class="org-main-avatar-img" alt="组织头像" />
          <el-icon v-else :size="48" color="#fff"><OfficeBuilding /></el-icon>
        </div>
        <div v-else class="org-avatar-empty">
          <el-icon :size="48"><OfficeBuilding /></el-icon>
        </div>
      </div>

      <div v-show="!collapsed" class="org-info-section" v-if="selectedOrg">
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

      <div v-show="!collapsed" class="org-info-section org-info-empty" v-else>
        <p class="org-empty-text">还未加入组织</p>
        <p class="org-empty-hint">请创建或加入一个组织</p>
      </div>

      <div v-show="!collapsed" class="org-actions">
        <template v-if="authStore.isAdmin">
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

    <div class="org-main" :class="{ collapsed }">
      <template v-if="organizations.length > 0">
        <Documents />
      </template>
      <div v-else class="org-no-org-hint">
        <el-icon :size="48"><OfficeBuilding /></el-icon>
        <p class="org-no-org-text">还未加入组织</p>
      </div>
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
  Plus, Key, CopyDocument, Camera, Calendar, OfficeBuilding, User, View, Hide, CirclePlusFilled, Connection, ArrowRight, ArrowLeft
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/modules/auth'
import { createOrganizationApi, joinByInviteCodeApi } from '@/api/organizations'
import type { Organization } from '@/types'
import Documents from '@/pages/Documents.vue'

const authStore = useAuthStore()
const collapsed = ref(false)
const showCreateDialog = ref(false)
const showJoinDialog = ref(false)
const createLoading = ref(false)
const joinLoading = ref(false)
const avatarInputRef = ref<HTMLInputElement | null>(null)
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

function isGradient(avatar: string): boolean {
  return avatar.startsWith('linear-gradient')
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
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
    const result = await createOrganizationApi({
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim() || undefined,
      avatar: createForm.value.avatar || undefined,
      phone: createForm.value.phone.trim() || undefined,
      email: createForm.value.email.trim() || undefined
    })
    ElMessage.success('组织创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '', avatar: '', avatarPreview: '', selectedDefault: '', phone: '', email: '' }
    await authStore.fetchCurrentUser()
    await authStore.fetchOrganizations()
    const orgId = (result as any)?.organization?.id
    if (orgId) {
      authStore.setCurrentOrg(orgId)
    }
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
    const result = await joinByInviteCodeApi({ code: joinForm.value.code.trim() })
    ElMessage.success('加入组织成功')
    showJoinDialog.value = false
    joinForm.value = { code: '' }
    await authStore.fetchCurrentUser()
    await authStore.fetchOrganizations()
    const orgId = (result as any)?.organization_id
    if (orgId) {
      authStore.setCurrentOrg(orgId)
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '加入失败')
  } finally {
    joinLoading.value = false
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
  try {
    await authStore.fetchOrganizations()
  } catch {
    // ignore
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
  padding: 20px 24px 24px;
  flex-shrink: 0;
  transition: width var(--transition-base);
  overflow: hidden;
}

.org-sidebar.collapsed {
  width: 50px;
  padding: 20px 0 24px;
  align-items: center;
}

.org-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.org-sidebar.collapsed .org-sidebar-header {
  justify-content: center;
  margin-bottom: 16px;
}

.org-sidebar-toggle {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: background var(--transition-fast), color var(--transition-fast);
  flex-shrink: 0;
}

.org-sidebar-toggle:hover {
  background: var(--color-bg);
  color: var(--color-primary);
}

.org-sidebar-spacer {
  flex: 1;
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

.org-action-card-icon-create {
  background: var(--gradient-primary);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.org-action-card-icon-join {
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

.org-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.org-main :deep(.documents-page) {
  width: 100%;
  height: 100%;
  padding: 24px 28px 32px;
}

.org-main.collapsed {
  align-items: center;
}

.org-main.collapsed :deep(.documents-page) {
  max-width: 1200px;
}

.org-no-org-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex: 1;
  color: var(--color-text-muted);
}

.org-no-org-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-muted);
  margin: 0;
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
}
</style>
