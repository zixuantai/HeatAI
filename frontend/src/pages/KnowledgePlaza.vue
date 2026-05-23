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
            <div class="kb-card-cover-icon" :style="{ background: kb.coverColor || 'var(--gradient-primary)' }">
              <el-icon :size="28"><FolderOpened /></el-icon>
            </div>
          </div>
          <div class="kb-card-body">
            <div class="kb-card-title-row">
              <h3 class="kb-card-title">{{ kb.name }}</h3>
              <el-tag v-if="kb.isRecommended" type="warning" size="small" effect="dark">精选</el-tag>
            </div>
            <p class="kb-card-desc">{{ kb.description || '暂无描述' }}</p>
            <div class="kb-card-meta">
              <span class="kb-card-meta-item">
                <el-icon :size="14"><Document /></el-icon>
                {{ kb.docCount }} 份文档
              </span>
              <span class="kb-card-meta-item">
                <el-icon :size="14"><User /></el-icon>
                {{ kb.ownerName }}
              </span>
              <span class="kb-card-meta-item">
                <el-icon :size="14"><View /></el-icon>
                {{ kb.viewCount }} 次浏览
              </span>
            </div>
            <div class="kb-card-footer">
              <span class="kb-card-date">{{ formatDate(kb.createdAt) }}</span>
              <div class="kb-card-actions">
                <button 
                  class="kb-action-btn" 
                  :class="{ 'is-liked': kb.isLiked }"
                  @click.stop="handleLike(kb)"
                >
                  <svg v-if="!kb.isLiked" class="thumb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                  </svg>
                  <svg v-else class="thumb-icon" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="0">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                  </svg>
                  <span>{{ kb.likeCount }}</span>
                </button>
                <button 
                  class="kb-action-btn"
                  :class="{ 'is-favorited': kb.isFavorited }"
                  @click.stop="handleFavorite(kb)"
                >
                  <el-icon :size="14">
                    <component :is="kb.isFavorited ? StarFilled : Star" />
                  </el-icon>
                  <span>收藏</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, Plus, FolderOpened, Document, User, View, Star, StarFilled, Collection, CollectionTag, Promotion
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface KnowledgeBase {
  id: string
  name: string
  description: string
  ownerName: string
  docCount: number
  viewCount: number
  likeCount: number
  isRecommended: boolean
  isLiked?: boolean
  isFavorited?: boolean
  coverColor?: string
  createdAt: string
}

const router = useRouter()
const searchQuery = ref('')
const activeTab = ref('recommended')
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(8)
const total = ref(0)
const knowledgeBases = ref<KnowledgeBase[]>([])

const tabs = [
  { key: 'recommended', label: '精选推荐' },
  { key: 'popular', label: '最热' },
  { key: 'latest', label: '最新' },
  { key: 'mine', label: '我的' }
]

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

const mockData: KnowledgeBase[] = [
  {
    id: '1',
    name: '供热工程技术规范知识库',
    description: '包含供热工程设计、施工、验收等全流程技术规范文档',
    ownerName: '技术部',
    docCount: 156,
    viewCount: 2340,
    likeCount: 89,
    isRecommended: true,
    createdAt: '2026-05-20T10:00:00Z'
  },
  {
    id: '2',
    name: '热力学基础知识库',
    description: '涵盖热力学基本原理、传热学、流体力学等基础知识',
    ownerName: '研发部',
    docCount: 98,
    viewCount: 1890,
    likeCount: 67,
    isRecommended: true,
    createdAt: '2026-05-18T14:30:00Z'
  },
  {
    id: '3',
    name: '智能供热系统知识库',
    description: '介绍智能供热系统的架构、算法和优化策略',
    ownerName: 'AI团队',
    docCount: 234,
    viewCount: 3560,
    likeCount: 156,
    isRecommended: false,
    createdAt: '2026-05-15T09:15:00Z'
  },
  {
    id: '4',
    name: '供热管网设计手册',
    description: '管网规划、设计计算、材料选型等专业资料',
    ownerName: '设计院',
    docCount: 78,
    viewCount: 1230,
    likeCount: 45,
    isRecommended: false,
    createdAt: '2026-05-12T16:45:00Z'
  },
  {
    id: '5',
    name: '节能减排政策法规',
    description: '国家及地方供热行业节能减排相关政策法规汇编',
    ownerName: '政策研究室',
    docCount: 67,
    viewCount: 890,
    likeCount: 34,
    isRecommended: true,
    createdAt: '2026-05-10T11:20:00Z'
  },
  {
    id: '6',
    name: '锅炉运行维护知识库',
    description: '各类锅炉设备的运行规程、维护保养和故障处理',
    ownerName: '运维部',
    docCount: 145,
    viewCount: 2100,
    likeCount: 78,
    isRecommended: false,
    createdAt: '2026-05-08T08:30:00Z'
  }
]

async function loadKnowledgeBases() {
  loading.value = true
  await new Promise(resolve => setTimeout(resolve, 500))
  
  let filtered = [...mockData]
  
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.trim().toLowerCase()
    filtered = filtered.filter(kb => 
      kb.name.toLowerCase().includes(query) || 
      kb.description.toLowerCase().includes(query)
    )
  }
  
  switch (activeTab.value) {
    case 'recommended':
      filtered = filtered.filter(kb => kb.isRecommended)
      break
    case 'popular':
      filtered.sort((a, b) => b.viewCount - a.viewCount)
      break
    case 'latest':
      filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      break
    case 'mine':
      filtered = []
      break
  }
  
  total.value = filtered.length
  const start = (currentPage.value - 1) * pageSize.value
  knowledgeBases.value = filtered.slice(start, start + pageSize.value).map((kb, i) => ({
    ...kb,
    coverColor: coverColors[i % coverColors.length]
  }))
  
  loading.value = false
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
  ElMessage.info('创建知识库功能开发中...')
}

function handleCardClick(kb: KnowledgeBase) {
  ElMessage.info(`查看知识库: ${kb.name}`)
}

function handleLike(kb: KnowledgeBase) {
  if (kb.isLiked) {
    kb.isLiked = false
    kb.likeCount--
  } else {
    kb.isLiked = true
    kb.likeCount++
  }
}

function handleFavorite(kb: KnowledgeBase) {
  kb.isFavorited = !kb.isFavorited
  if (kb.isFavorited) {
    ElMessage.success('收藏成功')
  } else {
    ElMessage.info('已取消收藏')
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
  width: 380px;
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