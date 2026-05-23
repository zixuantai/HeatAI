<template>
  <div class="plaza-page">
    <div class="plaza-header">
      <h1 class="plaza-title">
        <el-icon :size="24"><Promotion /></el-icon>
        知识库广场
      </h1>
    </div>

    <div class="plaza-toolbar">
      <div class="plaza-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="plaza-tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="handleTabChange(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="plaza-toolbar-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索知识库..."
          clearable
          size="large"
          class="plaza-search-input"
          @keyup.enter="handleSearch"
          @clear="handleClearSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <button class="plaza-btn-create" @click="handleCreate">
          <el-icon :size="16"><Plus /></el-icon>
          创建
        </button>
      </div>
    </div>

    <div class="plaza-list">
      <div v-loading="loading" class="plaza-cards-wrapper">
        <div
          v-for="kb in knowledgeBases"
          :key="kb.id"
          class="kb-card"
          @click="handleCardClick(kb)"
        >
          <div class="kb-card-cover">
            <div class="kb-card-cover-icon" :style="{ background: kb.cover_color || 'var(--gradient-primary)' }">
              <el-icon :size="28"><FolderOpened /></el-icon>
            </div>
          </div>
          <div class="kb-card-body">
            <div class="kb-card-title-row">
              <h3 class="kb-card-title">{{ kb.name }}</h3>
              <el-tag v-if="kb.is_recommended" type="warning" size="small" effect="dark">精选</el-tag>
            </div>
            <p class="kb-card-desc">{{ kb.description || '暂无描述' }}</p>
            <div class="kb-card-meta">
              <span class="kb-card-meta-item">
                <el-icon :size="14"><Document /></el-icon>
                {{ kb.doc_count }} 份文档
              </span>
              <span class="kb-card-meta-item">
                <el-icon :size="14"><User /></el-icon>
                {{ kb.owner_name || '未知' }}
              </span>
              <span class="kb-card-meta-item">
                <el-icon :size="14"><View /></el-icon>
                {{ kb.view_count }} 次浏览
              </span>
            </div>
            <div class="kb-card-footer">
              <span class="kb-card-date">{{ formatDate(kb.created_at) }}</span>
              <div class="kb-card-actions">
                <button 
                  class="kb-action-btn" 
                  :class="{ 'is-liked': kb.is_liked }"
                  @click.stop="handleLike(kb)"
                >
                  <svg v-if="!kb.is_liked" class="thumb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                  </svg>
                  <svg v-else class="thumb-icon" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="0">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                  </svg>
                  <span>{{ kb.like_count }}</span>
                </button>
                <button 
                  class="kb-action-btn"
                  :class="{ 'is-favorited': kb.is_favorited }"
                  @click.stop="handleFavorite(kb)"
                >
                  <el-icon :size="14">
                    <component :is="kb.is_favorited ? StarFilled : Star" />
                  </el-icon>
                  <span>收藏</span>
                </button>
                <button
                  v-if="activeTab === 'mine'"
                  class="kb-action-btn delete-btn"
                  @click.stop="handleDelete(kb)"
                >
                  <el-icon :size="14"><Delete /></el-icon>
                  <span>删除</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <el-empty
          v-if="!loading && knowledgeBases.length === 0"
          description="暂无知识库"
          class="kb-empty"
        />
      </div>
    </div>

    <div class="plaza-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[8, 16, 24, 32, 40]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <CreateKnowledgeBaseDialog v-model="showCreateDialog" @created="handleCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, Plus, FolderOpened, Document, User, View, Star, StarFilled, Promotion, Delete
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { KnowledgeBase } from '@/types'
import { getKnowledgeBasesApi, toggleLikeApi, toggleFavoriteApi, deleteKnowledgeBaseApi } from '@/api/knowledgeBases'
import CreateKnowledgeBaseDialog from '@/components/plaza/CreateKnowledgeBaseDialog.vue'

const router = useRouter()
const searchQuery = ref('')
const activeTab = ref('recommended')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(8)
const total = ref(0)
const knowledgeBases = ref<KnowledgeBase[]>([])
const showCreateDialog = ref(false)

const tabs = [
  { key: 'recommended', label: '精选推荐' },
  { key: 'popular', label: '最热' },
  { key: 'latest', label: '最新' },
  { key: 'mine', label: '我的' }
]

const sortMap: Record<string, string> = {
  recommended: 'recommended',
  popular: 'popular',
  latest: 'latest',
  mine: 'mine'
}

async function loadKnowledgeBases() {
  loading.value = true
  try {
    const result = await getKnowledgeBasesApi({
      search: searchQuery.value.trim() || undefined,
      sort_by: sortMap[activeTab.value] || 'latest',
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    })
    knowledgeBases.value = result.items
    total.value = result.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleTabChange(tab: string) {
  activeTab.value = tab
  currentPage.value = 1
  loadKnowledgeBases()
}

function handleSearch() {
  currentPage.value = 1
  loadKnowledgeBases()
}

function handleClearSearch() {
  searchQuery.value = ''
  currentPage.value = 1
  loadKnowledgeBases()
}

function handleCreate() {
  showCreateDialog.value = true
}

function handleCreated() {
  loadKnowledgeBases()
}

function handleCardClick(kb: KnowledgeBase) {
  router.push(`/plaza/${kb.id}/chat`)
}

async function handleLike(kb: KnowledgeBase) {
  try {
    const result = await toggleLikeApi(kb.id)
    kb.is_liked = result.is_liked
    kb.like_count += result.is_liked ? 1 : -1
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function handleFavorite(kb: KnowledgeBase) {
  try {
    const result = await toggleFavoriteApi(kb.id)
    kb.is_favorited = result.is_favorited
    ElMessage.success(result.is_favorited ? '收藏成功' : '已取消收藏')
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

async function handleDelete(kb: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库「${kb.name}」吗？删除后所有关联的对话将无法访问。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteKnowledgeBaseApi(kb.id)
    ElMessage.success('知识库已删除')
    loadKnowledgeBases()
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadKnowledgeBases()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadKnowledgeBases()
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.plaza-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 28px 80px;
  height: 100vh;
  overflow-y: auto;
  position: relative;
}

.plaza-header {
  margin-bottom: 20px;
}

.plaza-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  color: var(--color-text-main);
  margin: 0;
  letter-spacing: var(--tracking-tight);
}

.plaza-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.plaza-toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plaza-search-input {
  width: 560px;
  height: 38px;
}

.plaza-search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-full) !important;
  box-shadow: none !important;
  border: 1px solid var(--color-border) !important;
  background: var(--color-surface);
  height: 100%;
  padding: 0 20px;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.plaza-search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary) !important;
}

.plaza-search-input :deep(.el-input.is-focus .el-input__wrapper) {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08) !important;
}

.plaza-btn-create {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-full);
  padding: 9px 18px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
  transition: all 150ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
  font-family: var(--font-family);
  flex-shrink: 0;
}

.plaza-btn-create:hover {
  box-shadow: 0 6px 22px rgba(79, 70, 229, 0.5);
  transform: translateY(-1px);
}

.plaza-btn-create:active {
  transform: translateY(2px);
  box-shadow: inset 3px 3px 8px rgba(0,0,0,0.2), inset -3px -3px 8px rgba(255,255,255,0.1);
}

.plaza-tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--color-surface);
  border-radius: var(--radius-full);
  box-shadow: var(--neu-recessed);
}

.plaza-tab-btn {
  padding: 8px 18px;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all 200ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
  font-family: var(--font-family);
  white-space: nowrap;
}

.plaza-tab-btn:hover {
  color: var(--color-text-main);
}

.plaza-tab-btn.active {
  background: var(--gradient-primary);
  color: #fff;
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
}

.plaza-list {
  min-height: 300px;
}

.plaza-cards-wrapper {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.kb-empty {
  grid-column: 1 / -1;
}

.kb-card {
  display: flex;
  gap: 16px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  padding: 18px;
  cursor: pointer;
  box-shadow: var(--neu-card);
  transition: transform 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.35s ease-out;
}

.kb-card:hover {
  transform: translateY(-4px);
  box-shadow:
    8px 8px 20px var(--neu-shadow-dark),
    -8px -8px 20px var(--neu-shadow-light),
    0 12px 28px rgba(0, 0, 0, 0.12);
}

.kb-card-cover {
  flex-shrink: 0;
}

.kb-card-cover-icon {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.kb-card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.kb-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.kb-card-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-card-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 0 0 10px;
  line-height: var(--leading-relaxed);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-card-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.kb-card-meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.kb-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}

.kb-card-date {
  font-size: 11px;
  color: var(--color-text-muted);
}

.kb-card-actions {
  display: flex;
  gap: 6px;
}

.kb-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all 150ms ease;
  font-family: var(--font-family);
}

.kb-action-btn .thumb-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.kb-action-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.04);
}

.kb-action-btn.is-liked {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
}

.kb-action-btn.is-favorited {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
}

.kb-action-btn.delete-btn:hover {
  border-color: var(--color-error);
  color: var(--color-error);
  background: rgba(229, 62, 62, 0.08);
}

.plaza-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 32px;
  padding-top: 4px;
}

.plaza-pagination :deep(.el-pagination .is-active) {
  background-color: var(--color-secondary);
  color: #fff;
}

.plaza-pagination :deep(.el-pagination .el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--color-secondary) inset;
}

@media (max-width: 1024px) {
  .plaza-cards-wrapper {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .plaza-page {
    padding: 20px 16px 60px;
  }

  .plaza-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .plaza-toolbar-right {
    width: 100%;
    flex-direction: column;
  }

  .plaza-search-input {
    width: 100%;
  }

  .plaza-btn-create {
    width: 100%;
    justify-content: center;
  }

  .plaza-tabs {
    width: 100%;
    overflow-x: auto;
  }
}
</style>
