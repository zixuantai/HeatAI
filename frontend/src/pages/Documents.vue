<template>
  <div class="documents-page">
    <!-- ── 页面头部 ────────────────────────────── -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <el-icon :size="24"><FolderOpened /></el-icon>
          知识库文档管理
        </h1>
        <p class="page-desc">上传、管理和检索知识库文档，支持 PDF、Word、HTML、TXT 格式</p>
      </div>
    </div>

    <!-- ── 上传区域 ────────────────────────────── -->
    <div class="upload-zone neu-card"
      :class="{ 'is-dragover': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInputRef"
        type="file"
        accept=".pdf,.docx,.doc,.html,.htm,.txt,.md,.markdown,.csv,.json,.xlsx,.xls,.pptx,.ppt,.epub,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
        multiple
        style="display: none"
        @change="handleFileSelect"
      />
      <div class="upload-content" @click="fileInputRef?.click()">
        <div class="upload-icon-housing">
          <el-icon :size="36" class="upload-icon"><UploadFilled /></el-icon>
        </div>
        <p class="upload-text">点击或拖拽文件到此处上传</p>
        <p class="upload-hint">支持 PDF · Word · Excel · PPT · HTML · TXT · Markdown · CSV · JSON · EPUB · 图片，单文件最大 50MB</p>
      </div>
    </div>

    <div class="upload-notice">
      <el-icon :size="16"><InfoFilled /></el-icon>
      <span>上传文档后需经过解析、分块、向量化等处理步骤，请耐心等待</span>
    </div>

    <!-- ── 知识库文档数据展示 ────────────────────── -->
    <div class="stats-section neu-card" v-if="statsData && statsData.total > 0">
      <h3 class="stats-title">知识库文档数据展示</h3>
      <div class="stats-charts">
        <!-- 文档类型分布 -->
        <div class="stats-chart-item">
          <h4 class="chart-label">文档类型分布</h4>
          <div class="donut-wrapper">
            <svg viewBox="0 0 160 160" class="donut-chart">
              <circle
                v-for="(seg, i) in fileTypeSegments"
                :key="i"
                cx="80" cy="80" r="54"
                fill="none"
                stroke-width="26"
                :stroke="seg.color"
                :stroke-dasharray="seg.dashArray"
                :stroke-dashoffset="seg.dashOffset"
                stroke-linecap="butt"
                transform="rotate(-90 80 80)"
              />
              <circle cx="80" cy="80" r="41" fill="var(--color-bg)" />
              <text x="80" y="76" text-anchor="middle" class="donut-center-num">{{ statsData.total }}</text>
              <text x="80" y="94" text-anchor="middle" class="donut-center-label">文档总数</text>
            </svg>
            <div class="donut-legend">
              <div v-for="item in statsData.by_file_type" :key="item.type" class="legend-item">
                <span class="legend-dot" :style="{ background: getFileTypeColor(item.type) }"></span>
                <span class="legend-name">{{ formatFileTypeLabel(item.type) }}</span>
                <span class="legend-count">{{ item.count }}</span>
              </div>
              <div v-if="statsData.by_file_type.length === 0" class="legend-empty">暂无数据</div>
            </div>
          </div>
        </div>

        <!-- 文档分类分布 -->
        <div class="stats-chart-item">
          <h4 class="chart-label">文档分类分布</h4>
          <div class="donut-wrapper">
            <svg viewBox="0 0 160 160" class="donut-chart">
              <circle
                v-for="(seg, i) in categorySegments"
                :key="i"
                cx="80" cy="80" r="54"
                fill="none"
                stroke-width="26"
                :stroke="seg.color"
                :stroke-dasharray="seg.dashArray"
                :stroke-dashoffset="seg.dashOffset"
                stroke-linecap="butt"
                transform="rotate(-90 80 80)"
              />
              <circle cx="80" cy="80" r="41" fill="var(--color-bg)" />
              <text x="80" y="76" text-anchor="middle" class="donut-center-num">{{ statsData.total }}</text>
              <text x="80" y="94" text-anchor="middle" class="donut-center-label">文档总数</text>
            </svg>
            <div class="donut-legend">
              <div v-for="(item, i) in statsData.by_category" :key="item.category" class="legend-item">
                <span class="legend-dot" :style="{ background: categoryColors[i % categoryColors.length] }"></span>
                <span class="legend-name">{{ item.category }}</span>
                <span class="legend-count">{{ item.count }}</span>
              </div>
              <div v-if="statsData.by_category.length === 0" class="legend-empty">暂无分类数据</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 搜索区 ──────────────────────────────── -->
    <div v-if="uploadingFiles.length > 0" class="upload-progress-section">
      <div class="upload-progress-summary neu-card" @click="uploadProgressCollapsed = !uploadProgressCollapsed">
        <div class="summary-left">
          <div class="summary-icon-housing" :class="{ 'is-done': uploadStats.allDone }">
            <el-icon :size="18" class="summary-icon" :class="{ 'is-loading': !uploadStats.allDone }">
              <component :is="uploadStats.allDone ? 'CircleCheckFilled' : 'Loading'" />
            </el-icon>
          </div>
          <span class="summary-text">
            <template v-if="uploadStats.active > 0">
              正在处理 <strong>{{ uploadStats.uploading }}</strong> 个
              <template v-if="uploadStats.pending > 0">
                ，排队等待 <strong class="text-pending">{{ uploadStats.pending }}</strong> 个
              </template>
            </template>
            <template v-else>
              全部处理完成
            </template>
            <template v-if="uploadStats.completed > 0">
              ，已完成 <strong class="text-success">{{ uploadStats.completed }}</strong> 个
            </template>
            <template v-if="uploadStats.failed > 0">
              ，失败 <strong class="text-danger">{{ uploadStats.failed }}</strong> 个
            </template>
          </span>
        </div>
        <div class="summary-right">
          <el-button
            v-if="uploadStats.allDone"
            text
            size="small"
            type="info"
            @click.stop="clearCompletedUploads"
          >
            <el-icon :size="14"><Close /></el-icon>
            清除记录
          </el-button>
          <el-icon :size="16" class="collapse-icon" :class="{ 'is-collapsed': uploadProgressCollapsed }">
            <ArrowDown />
          </el-icon>
        </div>
      </div>

      <div v-show="!uploadProgressCollapsed" class="upload-progress-list neu-recessed">
        <div v-for="uf in pagedUploadingFiles" :key="uf.name" class="upload-progress-item">
          <div class="upload-progress-info">
            <el-icon :class="{ 'is-error': uf.status === 'error' }">
              <component :is="uf.status === 'success' ? 'CircleCheck' : uf.status === 'error' ? 'CircleClose' : uf.status === 'pending' ? 'Clock' : 'Document'" />
            </el-icon>
            <span class="upload-progress-name" :title="uf.error || uf.name">{{ uf.name }}</span>
            <el-tag v-if="uf.status === 'pending'" type="info" size="small">排队中</el-tag>
            <el-tag v-else-if="uf.status === 'uploading'" type="warning" size="small">处理中</el-tag>
            <el-tag v-else-if="uf.status === 'success'" type="success" size="small">完成</el-tag>
            <el-tag v-else type="danger" size="small">失败</el-tag>
            <el-button
              v-if="uf.status === 'success' || uf.status === 'error'"
              text
              size="small"
              type="info"
              @click.stop="removeUploadRecord(uf.name)"
            >
              <el-icon :size="12"><Close /></el-icon>
            </el-button>
          </div>
          <div v-if="uf.status === 'uploading'" class="upload-progress-bar">
            <div class="upload-progress-fill"></div>
          </div>
        </div>

        <div v-if="activeUploadingFiles.length > uploadProgressPageSize" class="upload-progress-pagination">
          <span class="pagination-count">共 {{ activeUploadingFiles.length }} 项</span>
          <el-pagination
            v-model:current-page="uploadProgressPage"
            :page-size="uploadProgressPageSize"
            :total="activeUploadingFiles.length"
            layout="total, prev, pager, next"
            size="small"
            background
          />
        </div>
      </div>
    </div>

    <!-- ── 搜索区 ──────────────────────────────── -->
    <div class="search-section neu-card">
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="输入文档名搜索..."
          clearable
          size="large"
          class="neu-search-input"
          @keyup.enter="handleSearch"
          @clear="handleClearSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <button class="neu-btn-primary" @click="handleSearch">搜索</button>
      </div>
    </div>

    <!-- ── 文档列表 ────────────────────────────── -->
    <div class="documents-section neu-card">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-title-text">
            <template v-if="isSearching">搜索结果：<strong>{{ total }}</strong> 个文档</template>
            <template v-else>知识库文档</template>
          </span>
          <button
            v-if="!batchMode"
            class="neu-btn-primary neu-btn-primary--sm"
            @click="enterBatchMode"
          >
            <el-icon :size="14"><Delete /></el-icon>
            批量删除
          </button>
        </div>
        <div class="section-header-right">
          <!-- 视图切换 -->
          <div class="view-toggle neu-recessed">
            <button
              class="view-toggle-btn"
              :class="{ active: viewMode === 'card' }"
              @click="viewMode = 'card'"
              title="卡片视图"
            >
              <el-icon :size="16"><Grid /></el-icon>
            </button>
            <button
              class="view-toggle-btn"
              :class="{ active: viewMode === 'table' }"
              @click="viewMode = 'table'"
              title="表格视图"
            >
              <el-icon :size="16"><List /></el-icon>
            </button>
          </div>
          <button class="neu-btn-ghost" :disabled="loading" @click="handleRefresh">
            <el-icon :size="14"><Refresh /></el-icon>
            刷新
          </button>
        </div>
      </div>

      <!-- 批量操作栏 -->
      <div v-if="batchMode" class="batch-action-bar neu-recessed">
        <div class="batch-action-left">
          <span class="batch-check-group">
            <el-checkbox
              :model-value="selectAllPage"
              :indeterminate="isIndeterminatePage"
              size="large"
              @change="toggleSelectAllPage"
            >
              全选本页
            </el-checkbox>
            <el-checkbox
              :model-value="selectAllKB"
              :indeterminate="isIndeterminateKB"
              :disabled="allKbIdsLoading"
              size="large"
              @change="toggleSelectAllKB"
            >
              全选知识库
            </el-checkbox>
          </span>
          <span class="batch-selected-count">
            已选 <strong>{{ selectedIds.size }}</strong> 项
          </span>
        </div>
        <div class="batch-action-right">
          <button
            class="neu-btn-danger"
            :disabled="selectedIds.size === 0"
            @click="handleBatchDelete"
          >
            <el-icon :size="14"><Delete /></el-icon>
            删除选中
          </button>
          <button class="neu-btn-ghost" @click="exitBatchMode">
            <el-icon :size="14"><Close /></el-icon>
            取消
          </button>
        </div>
      </div>

      <!-- 表格视图 -->
      <el-table
        v-if="viewMode === 'table'"
        v-loading="loading"
        :data="documents"
        stripe
        style="width: 100%"
        empty-text="暂无文档，请上传"
        highlight-current-row
        @row-click="handleRowClick"
      >
        <el-table-column v-if="batchMode" width="55" align="center">
          <template #default="{ row }">
            <el-checkbox
              :model-value="selectedIds.has(row.id)"
              size="large"
              @change="toggleSelect(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="original_filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <div class="file-type-cell">
              <span class="file-type-badge" :style="{ background: getFileTypeColor(row.file_type) }">
                {{ row.file_type.toUpperCase() }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="80" align="center" />
        <el-table-column prop="created_at" label="上传时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              text
              size="small"
              :loading="deletingIds.has(row.id)"
              @click.stop="handleDeleteClick(row)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 卡片视图 -->
      <div v-else class="doc-cards-grid">
        <div v-loading="loading" class="doc-cards-wrapper">
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="tilt-container"
            :class="{ 'is-batch-mode': batchMode, 'is-selected': batchMode && selectedIds.has(doc.id) }"
          >

            <div class="doc-card tilt-card" :data-doc-id="doc.id" @click="handleRowClick(doc)">
              <!-- 批量勾选框 -->
              <div v-if="batchMode" class="batch-card-check" @click.stop="toggleSelect(doc)">
                <el-checkbox
                  :model-value="selectedIds.has(doc.id)"
                  size="large"
                />
              </div>

              <!-- 角螺丝 -->
              <span class="neu-screw neu-screw-tl" />
              <span class="neu-screw neu-screw-tr" />
              <span class="neu-screw neu-screw-bl" />
              <span class="neu-screw neu-screw-br" />

              <!-- 散热槽 -->
              <div class="neu-vents">
                <span class="neu-vent" />
                <span class="neu-vent" />
                <span class="neu-vent" />
              </div>

              <!-- 顶部：文件类型图标 -->
              <div class="doc-card-top">
                <div
                  class="doc-type-badge"
                  :style="{ '--badge-color': getFileTypeColor(doc.file_type) }"
                >
                  <span class="doc-type-ext">{{ doc.file_type.toUpperCase() }}</span>
                  <svg class="doc-type-ring" viewBox="0 0 56 56">
                    <circle cx="28" cy="28" r="26" fill="none" stroke-width="2"
                      :stroke="getFileTypeColor(doc.file_type)" opacity="0.3" />
                  </svg>
                </div>
                <div class="doc-meta-row">
                <span
                  class="neu-led"
                  :class="{
                    'neu-led-online': doc.status === 'completed',
                    'neu-led-danger': doc.status === 'failed',
                    'neu-led-warning': doc.status === 'processing' || doc.status !== 'completed' && doc.status !== 'failed'
                  }"
                />
                <span class="doc-meta-label">
                  {{ doc.status === 'completed' ? 'INDEXED' : doc.status === 'failed' ? 'FAILED' : doc.status === 'processing' ? 'PROCESSING' : 'PENDING' }}
                </span>
              </div>
              </div>

              <!-- 中间：文件名 -->
              <h3 class="doc-card-name" :title="doc.original_filename">
                {{ doc.original_filename }}
              </h3>

              <!-- 底部：信息条 -->
              <div class="doc-card-info">
                <div class="doc-info-item">
                  <el-icon :size="14"><Coin /></el-icon>
                  <span>{{ formatFileSize(doc.file_size) }}</span>
                </div>
                <div class="doc-info-item">
                  <span class="doc-info-chip">{{ doc.chunk_count }} 块</span>
                </div>
                <div class="doc-info-item">
                  <el-icon :size="14"><Clock /></el-icon>
                  <span>{{ formatDateShort(doc.created_at) }}</span>
                </div>
              </div>

              <button
                class="neu-btn-delete"
                :class="{ 'is-deleting': deletingIds.has(doc.id) }"
                :disabled="deletingIds.has(doc.id)"
                @click.stop="handleDeleteClick(doc)"
              >
                <el-icon v-if="!deletingIds.has(doc.id)" :size="14"><Delete /></el-icon>
                <el-icon v-else :size="14" class="is-loading"><Loading /></el-icon>
              </button>
            </div>
          </div>

          <el-empty
            v-if="!loading && documents.length === 0"
            description="暂无文档，请上传"
            class="doc-empty"
          />
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="pageSizes"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>

    </div>

    <!-- ── 分块详情弹窗 ─────────────────────────── -->
    <el-dialog
      v-model="chunkDialogVisible"
      :title="chunkDialogTitle"
      width="800px"
      destroy-on-close
    >
      <div v-loading="chunkLoading" class="chunk-list">
        <div v-for="chunk in chunks" :key="chunk.id" class="chunk-item neu-recessed">
          <div class="chunk-header">
            <el-tag size="small" type="info">#{{ chunk.chunk_index }}</el-tag>
            <span class="chunk-title">{{ chunk.title }}</span>
          </div>
          <div class="chunk-content">{{ chunk.content }}</div>
        </div>
        <el-empty v-if="!chunkLoading && chunks.length === 0" description="暂无分块数据" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  FolderOpened, UploadFilled, Document, Delete, Refresh, Search, InfoFilled,
  Grid, List, Coin, Clock, Close, CircleCheckFilled, Loading, CircleCheck, CircleClose, ArrowDown
} from '@element-plus/icons-vue'
import type { DocumentInfo, DocumentStats } from '@/types'
import { useDocuments } from '@/composables/documents/useDocuments'
import { getAllDocumentIdsApi, getDocumentStatsApi } from '@/api/documents'
import {
  uploadingFiles,
  activeUploadingFiles,
  pagedUploadingFiles,
  uploadStats,
  uploadProgressCollapsed,
  uploadProgressPage,
  uploadProgressPageSize,
  uploadFiles,
  removeUploadRecord,
  clearCompletedUploads,
  useUploadLifecycle,
} from '@/composables/documents/useDocuments'

const fileInputRef = ref<HTMLInputElement>()
const isDragOver = ref(false)

const {
  loading,
  chunkLoading,
  deletingIds,
  documents,
  total,
  chunks,
  chunkDialogVisible,
  chunkDialogTitle,
  loadDocuments,
  deleteDocument: _deleteDocument,
  deleteDocumentsBatch: _deleteDocumentsBatch,
  loadDocumentChunks,
  refresh: _refresh,
} = useDocuments()

useUploadLifecycle(async () => {
  await loadDocuments(pageSize.value, 1)
  loadStats()
})

const currentPage = ref(1)
const pageSize = ref(12)

const searchQuery = ref('')
const isSearching = ref(false)
const viewMode = ref<'card' | 'table'>('card')

// 统计图表数据
const statsData = ref<DocumentStats | null>(null)

const categoryColors = [
  '#4F46E5', '#7C3AED', '#EC4899', '#F59E0B', '#10B981',
  '#06B6D4', '#EF4444', '#8B5CF6', '#F97316', '#14B8A6',
]

const CIRCLE_LENGTH = 2 * Math.PI * 54

function buildSegments(items: { count: number }[], colorGetter: (i: number) => string) {
  const total = items.reduce((s, it) => s + it.count, 0)
  if (total === 0) return []
  let offset = 0
  return items.map((item, i) => {
    const ratio = item.count / total
    const dashLen = ratio * CIRCLE_LENGTH
    const seg = {
      color: colorGetter(i),
      dashArray: `${dashLen} ${CIRCLE_LENGTH - dashLen}`,
      dashOffset: -offset,
    }
    offset += dashLen
    return seg
  })
}

const fileTypeSegments = computed(() => {
  if (!statsData.value) return []
  return buildSegments(statsData.value.by_file_type, (i) =>
    getFileTypeColor(statsData.value!.by_file_type[i].type)
  )
})

const categorySegments = computed(() => {
  if (!statsData.value) return []
  return buildSegments(statsData.value.by_category, (i) =>
    categoryColors[i % categoryColors.length]
  )
})

function formatFileTypeLabel(type: string): string {
  const map: Record<string, string> = {
    pdf: 'PDF', docx: 'Word', doc: 'Word', html: 'HTML', htm: 'HTML',
    txt: 'TXT', md: 'Markdown', csv: 'CSV', json: 'JSON',
    xlsx: 'Excel', xls: 'Excel', pptx: 'PPT', ppt: 'PPT',
    png: '图片', jpg: '图片', jpeg: '图片', bmp: '图片', tiff: '图片', webp: '图片',
    epub: 'EPUB',
  }
  return map[type.toLowerCase()] || type.toUpperCase()
}

async function loadStats() {
  try {
    const data = await getDocumentStatsApi()
    statsData.value = data
  } catch {
    statsData.value = null
  }
}

// 批量删除状态
const batchMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const allKbIds = ref<string[]>([])
const allKbIdsLoading = ref(false)
const isPageAllSelected = ref(false)

const selectAllPage = computed(() =>
  batchMode.value && documents.value.length > 0 && isPageAllSelected.value
)

const isIndeterminatePage = computed(() =>
  batchMode.value && documents.value.some(d => selectedIds.value.has(d.id)) && !documents.value.every(d => selectedIds.value.has(d.id))
)

const selectAllKB = computed(() => {
  if (!batchMode.value || allKbIds.value.length === 0) return false
  return allKbIds.value.every(id => selectedIds.value.has(id))
})

const isIndeterminateKB = computed(() => {
  if (!batchMode.value || allKbIds.value.length === 0) return false
  return allKbIds.value.some(id => selectedIds.value.has(id)) && !allKbIds.value.every(id => selectedIds.value.has(id))
})

function enterBatchMode() {
  batchMode.value = true
  selectedIds.value = new Set()
  allKbIds.value = []
  isPageAllSelected.value = false
}

function exitBatchMode() {
  batchMode.value = false
  selectedIds.value = new Set()
  allKbIds.value = []
  isPageAllSelected.value = false
}

function toggleSelect(doc: DocumentInfo) {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(doc.id)) {
    newSet.delete(doc.id)
  } else {
    newSet.add(doc.id)
  }
  selectedIds.value = newSet
  isPageAllSelected.value = documents.value.length > 0 && documents.value.every(d => newSet.has(d.id))
}

function toggleSelectAllPage(val: boolean) {
  isPageAllSelected.value = val
  if (val) {
    allKbIds.value = []
    const newSet = new Set<string>()
    documents.value.forEach(d => newSet.add(d.id))
    selectedIds.value = newSet
  } else {
    const newSet = new Set(selectedIds.value)
    documents.value.forEach(d => newSet.delete(d.id))
    selectedIds.value = newSet
  }
}

async function toggleSelectAllKB(val: boolean) {
  if (val) {
    isPageAllSelected.value = false
    allKbIdsLoading.value = true
    try {
      const res = await getAllDocumentIdsApi(isSearching.value ? searchQuery.value.trim() : undefined)
      const ids = res.ids || []
      allKbIds.value = ids
      selectedIds.value = new Set(ids)
    } catch {
      allKbIds.value = []
    } finally {
      allKbIdsLoading.value = false
    }
  } else {
    selectedIds.value = new Set()
    allKbIds.value = []
    isPageAllSelected.value = false
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.size === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedIds.value.size} 个文档吗？此操作不可撤销。`,
      '批量删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const ids = Array.from(selectedIds.value)
    exitBatchMode()
    const newPage = await _deleteDocumentsBatch(
      ids,
      pageSize.value,
      currentPage.value,
      isSearching.value,
      searchQuery.value.trim()
    )
    currentPage.value = newPage
  } catch {
    // 用户取消
  }
}

const pageSizes = computed(() => {
  return viewMode.value === 'card'
    ? [12, 24, 36, 48, 60, 72]
    : [10, 20, 50, 100]
})

watch(viewMode, (mode) => {
  currentPage.value = 1
  pageSize.value = mode === 'card' ? 12 : 10
})

function getFileTypeColor(fileType: string): string {
  const map: Record<string, string> = {
    pdf: '#e74c3c',
    docx: '#2b579a',
    doc: '#2b579a',
    html: '#e67e22',
    htm: '#e67e22',
    txt: '#7f8c8d',
  }
  return map[fileType.toLowerCase()] || '#94a3b8'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatDateShort(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

async function handleLoad(search?: string) {
  await loadDocuments(pageSize.value, currentPage.value, search)
}

async function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return
  currentPage.value = 1
  uploadFiles(Array.from(files))
}

function handleFileSelect() {
  const files = fileInputRef.value?.files
  if (!files || files.length === 0) return
  currentPage.value = 1
  uploadFiles(Array.from(files))
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function handleDeleteClick(doc: DocumentInfo) {
  try {
    await ElMessageBox.confirm(
      '确定要删除该文档吗？此操作不可撤销。',
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    const newPage = await _deleteDocument(doc.id, pageSize.value, currentPage.value, isSearching.value, searchQuery.value.trim())
    currentPage.value = newPage
  } catch {
    // 用户取消
  }
}

async function handleRowClick(row: DocumentInfo) {
  if (batchMode.value) {
    toggleSelect(row)
    return
  }
  await loadDocumentChunks(row)
}

async function handleSearch() {
  const q = searchQuery.value.trim()
  if (q) {
    isSearching.value = true
    currentPage.value = 1
    await handleLoad(q)
  } else {
    isSearching.value = false
    currentPage.value = 1
    await handleLoad()
  }
}

async function handleClearSearch() {
  searchQuery.value = ''
  isSearching.value = false
  currentPage.value = 1
  await handleLoad()
}

function handleRefresh() {
  _refresh(pageSize.value, currentPage.value, isSearching.value, searchQuery.value.trim())
}

function handlePageChange(page: number) {
  currentPage.value = page
  handleLoad(isSearching.value ? searchQuery.value.trim() : undefined)
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  handleLoad(isSearching.value ? searchQuery.value.trim() : undefined)
}

onMounted(() => {
  handleLoad()
  loadStats()
})
</script>

<style scoped>
/* ============================================================
   Documents Page — Industrial Neumorphic
   ============================================================ */

.documents-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 28px 80px;
  height: 100vh;
  overflow-y: auto;
  position: relative;
}

/* ── Atmospheric Background Blob ──────────────────── */
.documents-page::before {
  content: '';
  position: fixed;
  top: -15%;
  right: -10%;
  width: 500px;
  height: 500px;
  border-radius: 50%;
  background: rgba(79, 70, 229, 0.03);
  filter: blur(120px);
  z-index: -1;
  pointer-events: none;
}

/* ── Page Header ──────────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  gap: 20px;
}

.header-left {
  flex: 1;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  color: var(--color-text-main);
  margin: 0 0 8px;
  letter-spacing: var(--tracking-tight);
}

.page-desc {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  margin: 0;
  font-weight: var(--font-weight-medium);
}

.header-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  background: var(--color-surface);
  border-radius: var(--radius-full);
  box-shadow: var(--neu-recessed);
  flex-shrink: 0;
}

.status-label {
  font-family: var(--font-family);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

/* ── Search Section ──────────────────────────────── */
.search-section {
  padding: 22px 24px;
  margin-bottom: 20px;
}

/* ── Stats Section (知识库文档数据展示) ──────────── */
.stats-section {
  padding: 24px 28px;
  margin-bottom: 20px;
}

.stats-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin: 0 0 20px;
  letter-spacing: 0.02em;
}

.stats-charts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 32px;
}

.stats-chart-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.chart-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-muted);
  margin: 0 0 16px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.donut-wrapper {
  display: flex;
  align-items: center;
  gap: 24px;
}

.donut-chart {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
  filter: drop-shadow(2px 4px 8px rgba(0, 0, 0, 0.08));
}

.donut-center-num {
  font-family: var(--font-family);
  font-size: 20px;
  font-weight: 800;
  fill: var(--color-text-main);
}

.donut-center-label {
  font-family: var(--font-family);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  fill: var(--color-text-muted);
}

.donut-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 90px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-sm);
  white-space: nowrap;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-name {
  color: var(--color-text-main);
  font-weight: var(--font-weight-medium);
  flex: 1;
}

.legend-count {
  color: var(--color-text-muted);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-xs);
  background: var(--color-border-light);
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.legend-empty {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  padding: 4px 0;
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-bar :deep(.el-input) {
  flex: 1;
}

.search-bar :deep(.el-input__wrapper) {
  border-radius: var(--radius-sm) !important;
  box-shadow: none !important;
  border: 1px solid var(--color-border) !important;
  background: var(--color-surface);
  padding: 6px 20px;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.search-bar :deep(.el-input__wrapper:hover) {
  border-color: var(--color-primary) !important;
}

.search-bar :deep(.el-input.is-focus .el-input__wrapper) {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08) !important;
}

/* Neumorphic 主按钮 */
.neu-btn-primary {
  background: var(--gradient-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-full);
  padding: 12px 28px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
  transition: all 150ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
  font-family: var(--font-family);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}
.neu-btn-primary:hover {
  box-shadow: 0 6px 22px rgba(79, 70, 229, 0.5);
  transform: translateY(-1px);
}
.neu-btn-primary:active {
  transform: translateY(2px);
  box-shadow: inset 3px 3px 8px rgba(0,0,0,0.2), inset -3px -3px 8px rgba(255,255,255,0.1);
}

.neu-btn-primary--sm {
  padding: 8px 18px;
  font-size: var(--font-size-sm);
  text-transform: none;
  letter-spacing: 0.02em;
}

/* 危险操作按钮 */
.neu-btn-danger {
  background: linear-gradient(135deg, #f87171, #ef4444);
  color: #fff;
  border: none;
  border-radius: var(--radius-full);
  padding: 8px 18px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  box-shadow:
    3px 3px 8px rgba(239, 68, 68, 0.18),
    -3px -3px 8px rgba(255, 255, 255, 0.7);
  transition: all 150ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
  font-family: var(--font-family);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.neu-btn-danger:hover:not(:disabled) {
  box-shadow:
    5px 5px 14px rgba(239, 68, 68, 0.28),
    -4px -4px 12px rgba(255, 255, 255, 0.85);
  transform: translateY(-1px);
}
.neu-btn-danger:active:not(:disabled) {
  transform: translateY(1px);
  box-shadow:
    inset 2px 2px 6px rgba(185, 28, 28, 0.3),
    inset -2px -2px 6px rgba(255, 255, 255, 0.15);
}
.neu-btn-danger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

/* ── Upload Zone ─────────────────────────────────── */
.upload-zone {
  padding: 44px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 20px;
  border: 2px dashed var(--color-border) !important;
}

.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: var(--color-primary) !important;
  box-shadow: var(--neu-card-hover);
}

.upload-icon-housing {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-surface);
  box-shadow: var(--neu-card);
  margin-bottom: 16px;
  transition: box-shadow var(--transition-base), transform var(--transition-base);
}

.upload-zone:hover .upload-icon-housing,
.upload-zone.is-dragover .upload-icon-housing {
  box-shadow: var(--neu-card-hover);
  transform: translateY(-3px);
}

.upload-icon {
  color: var(--color-border);
  transition: color var(--transition-base);
}

.upload-zone:hover .upload-icon,
.upload-zone.is-dragover .upload-icon {
  color: var(--color-primary);
}

.upload-text {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  margin: 0 0 6px;
}

.upload-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
  font-weight: var(--font-weight-medium);
}

.upload-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px 18px;
  background: linear-gradient(135deg, #EEF2FF, #F5F3FF);
  border: 1px solid #C7D2FE;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  color: #4338CA;
  font-weight: var(--font-weight-medium);
}

/* ── Upload Progress ─────────────────────────────── */
.upload-progress-section {
  margin-bottom: 20px;
}

.upload-progress-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  transition: box-shadow var(--transition-base);
}

.upload-progress-summary:hover {
  box-shadow: var(--neu-card-hover);
}

.summary-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-icon-housing {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(79, 70, 229, 0.08);
  flex-shrink: 0;
  transition: all var(--transition-base);
}

.summary-icon-housing.is-done {
  background: rgba(34, 197, 94, 0.1);
}

.summary-icon {
  color: var(--color-primary);
  transition: color var(--transition-base);
}

.summary-icon-housing.is-done .summary-icon {
  color: #22c55e;
}

.summary-icon-housing:not(.is-done) {
  animation: processing-pulse 2s ease-in-out infinite;
}

@keyframes processing-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.3); }
  50% { box-shadow: 0 0 0 8px rgba(79, 70, 229, 0); }
}

.summary-text {
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  font-weight: var(--font-weight-medium);
}

.summary-text strong {
  font-weight: var(--font-weight-extrabold);
}

.summary-text .text-success {
  color: #22c55e;
}

.summary-text .text-danger {
  color: #ef4444;
}

.summary-text .text-pending {
  color: #f59e0b;
}

.summary-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-icon {
  transition: transform 200ms ease;
  color: var(--color-text-muted);
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

.upload-progress-list {
  margin-top: 4px;
  padding: 12px 14px;
  max-height: 340px;
  overflow-y: auto;
}

.upload-progress-item {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border-light);
  transition: background var(--transition-fast);
}

.upload-progress-item:last-child {
  border-bottom: none;
}

.upload-progress-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.upload-progress-info .el-icon {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.upload-progress-info .el-icon.is-error {
  color: #ef4444;
}

.upload-progress-name {
  flex: 1;
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: var(--font-weight-medium);
}

.upload-error-msg {
  margin-top: 6px;
  margin-left: 28px;
  font-size: var(--font-size-xs);
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
  padding: 4px 10px;
  border-radius: var(--radius-xs);
  word-break: break-all;
}

.upload-progress-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-top: 6px;
  margin-left: 28px;
}

.upload-progress-fill {
  height: 100%;
  width: 30%;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  animation: progress 1.8s ease-in-out infinite;
}

.upload-progress-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-light);
  margin-top: 4px;
  flex-wrap: wrap;
  gap: 8px;
}

.pagination-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

@keyframes progress {
  0% { width: 10%; }
  50% { width: 70%; }
  100% { width: 90%; }
}

/* ── Documents Section ───────────────────────────── */
.documents-section {
  padding: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.section-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-main);
}

.section-header-left strong {
  font-weight: var(--font-weight-extrabold);
  color: var(--color-primary);
}

.section-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 视图切换 */
.view-toggle {
  display: flex;
  padding: 4px;
  border-radius: var(--radius-full);
  gap: 2px;
}

.view-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 150ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.view-toggle-btn.active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: var(--neu-card);
}

.view-toggle-btn:hover:not(.active) {
  color: var(--color-text-main);
}

/* ── Card Grid ──────────────────────────────────── */
.doc-cards-grid {
  min-height: 200px;
}

.doc-cards-wrapper {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.doc-empty {
  grid-column: 1 / -1;
}

/* 3D 立体放大外层容器 */
.tilt-container {
  perspective: 800px;
  position: relative;
}

/* 文档卡片 */
.doc-card {
  position: relative;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  padding: 24px 20px 68px;
  cursor: pointer;
  box-shadow: var(--neu-card);
  overflow: hidden;
  height: 210px;
  transition: transform 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.35s ease-out;
}

.doc-card:hover {
  transform: scale(1.04) translateZ(18px);
  box-shadow:
    8px 8px 20px var(--neu-shadow-dark),
    -8px -8px 20px var(--neu-shadow-light),
    0 12px 28px rgba(0, 0, 0, 0.12);
}

.doc-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  background: radial-gradient(circle at 30% 20%, rgba(255,255,255,0.4), transparent 60%);
  pointer-events: none;
  opacity: 0.6;
  z-index: 0;
}

.doc-card-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  margin: 0 0 14px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
  position: relative;
  z-index: 1;
}

/* 顶部 */
.doc-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  position: relative;
  z-index: 1;
}

/* ── 高级感文件类型徽章 ────────────────────────── */
.doc-type-badge {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--badge-color, #4F46E5) 15%, white),
    color-mix(in srgb, var(--badge-color, #4F46E5) 8%, white)
  );
  box-shadow:
    inset 1px 1px 2px rgba(255,255,255,0.7),
    inset -1px -1px 2px rgba(0,0,0,0.06),
    2px 2px 6px rgba(0,0,0,0.08);
  border: 1.5px solid color-mix(in srgb, var(--badge-color, #4F46E5) 25%, transparent);
}

.doc-type-ring {
  position: absolute;
  inset: -4px;
  width: calc(100% + 8px);
  height: calc(100% + 8px);
  pointer-events: none;
}

.doc-type-ext {
  font-family: var(--font-family);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--badge-color, #4F46E5);
  position: relative;
  z-index: 1;
}

.doc-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-meta-label {
  font-family: var(--font-family);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

/* 底部信息条 */
.doc-card-info {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  position: relative;
  z-index: 1;
}

.doc-info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.doc-info-chip {
  font-family: var(--font-family);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.neu-btn-delete {
  position: absolute;
  bottom: 16px;
  right: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: var(--color-surface);
  box-shadow: 3px 3px 8px rgba(0,0,0,0.12), -2px -2px 6px rgba(255,255,255,0.9);
  color: var(--color-text-muted);
  cursor: pointer;
  z-index: 10;
  transition: all 150ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.neu-btn-delete:hover {
  color: #e74c3c;
  box-shadow: inset 3px 3px 6px rgba(0,0,0,0.1), inset -3px -3px 6px rgba(255,255,255,0.7);
  transform: scale(1.1);
}
.neu-btn-delete:active {
  transform: scale(0.95);
}

/* ── Table View ──────────────────────────────────── */
.documents-section :deep(.el-table__body-wrapper) {
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.documents-section :deep(.el-table__body tr) {
  cursor: pointer;
  transition: box-shadow var(--transition-base), background-color var(--transition-base);
}

.documents-section :deep(.el-table__body tr:hover) {
  box-shadow: var(--shadow-card);
  position: relative;
  z-index: 1;
}

.documents-section :deep(.el-table__body tr:hover > td) {
  background-color: rgba(79, 70, 229, 0.03) !important;
}

.documents-section :deep(.el-table__body tr.current-row > td) {
  background-color: rgba(79, 70, 229, 0.05) !important;
}

.documents-section :deep(.el-checkbox__input.is-checked .el-checkbox__inner),
.documents-section :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: var(--color-secondary);
  border-color: var(--color-secondary);
}

.documents-section :deep(.el-checkbox__input.is-checked:hover .el-checkbox__inner),
.documents-section :deep(.el-checkbox__input.is-indeterminate:hover .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

/* ── Table File Type Badge ───────────────────────── */
.file-type-cell {
  display: flex;
  align-items: center;
}

.file-type-badge {
  font-family: var(--font-family);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #fff;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  text-transform: uppercase;
}

/* ── Pagination ──────────────────────────────────── */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 4px;
}

.pagination-wrapper :deep(.el-pagination .is-active) {
  background-color: var(--color-secondary);
  color: #fff;
}

.pagination-wrapper :deep(.el-pagination .el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--color-secondary) inset;
}

/* ── 批量操作栏 ──────────────────────────────────── */
.batch-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  margin-bottom: 18px;
  gap: 16px;
  flex-wrap: wrap;
  border-radius: var(--radius-sm);
   background: var(--color-surface);
 }

 .batch-action-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.batch-check-group {
  display: flex;
  align-items: center;
  gap: 0;
}

.batch-check-group :deep(.el-checkbox) {
  margin-right: 10px;
}

.batch-action-left :deep(.el-checkbox__label) {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  color: var(--color-text-main);
}

.batch-action-left :deep(.el-checkbox__input.is-checked .el-checkbox__inner),
.batch-action-left :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: var(--color-secondary);
  border-color: var(--color-secondary);
}

.batch-action-left :deep(.el-checkbox__input.is-checked:hover .el-checkbox__inner),
.batch-action-left :deep(.el-checkbox__input.is-indeterminate:hover .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

.batch-selected-count {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.batch-selected-count strong {
  color: var(--color-primary);
  font-weight: var(--font-weight-extrabold);
}

.batch-action-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 卡片批量选中状态 */
.tilt-container.is-batch-mode {
  cursor: default;
}

.tilt-container.is-batch-mode .doc-card {
  cursor: pointer;
}

.tilt-container.is-selected .doc-card {
  border-color: var(--color-secondary) !important;
  box-shadow:
    inset 2px 2px 6px rgba(124, 58, 237, 0.12),
    inset -2px -2px 6px rgba(124, 58, 237, 0.04),
    3px 3px 10px var(--neu-shadow-dark),
    -3px -3px 10px var(--neu-shadow-light);
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.04), var(--color-surface));
}

.batch-card-check {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 20;
  width: 30px;
  height: 30px;
  background: var(--color-surface);
  border-radius: var(--radius-xs);
  padding: 0;
  box-shadow:
    2px 2px 6px var(--neu-shadow-dark),
    -2px -2px 6px var(--neu-shadow-light);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: box-shadow 150ms ease-out;
}

.tilt-container.is-selected .batch-card-check {
  box-shadow: var(--neu-pressed);
}

.batch-card-check :deep(.el-checkbox__input.is-checked .el-checkbox__inner),
.batch-card-check :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: var(--color-secondary);
  border-color: var(--color-secondary);
}

.batch-card-check :deep(.el-checkbox__input.is-checked:hover .el-checkbox__inner),
.batch-card-check :deep(.el-checkbox__input.is-indeterminate:hover .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

/* ── Chunk Dialog ────────────────────────────────── */
.chunk-list {
  max-height: 500px;
  overflow-y: auto;
  padding: 0 4px;
}

.chunk-item {
  padding: 16px 18px;
  margin-bottom: 12px;
  transition: box-shadow var(--transition-base);
}

.chunk-item:hover {
  box-shadow: var(--neu-card);
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.chunk-title {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.chunk-content {
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  line-height: var(--leading-relaxed);
  white-space: pre-wrap;
  word-break: break-word;
}

/* ============================================================
   Responsive
   ============================================================ */

@media (max-width: 1024px) {
  .doc-cards-wrapper {
    grid-template-columns: repeat(2, 1fr);
  }

  .stats-charts {
    grid-template-columns: 1fr;
    gap: 24px;
  }
}

@media (max-width: 768px) {
  .documents-page {
    padding: 20px 16px 60px;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-status {
    align-self: flex-start;
  }

  .search-bar {
    flex-direction: column;
  }

  .neu-btn-primary {
    width: 100%;
  }

  .upload-zone {
    padding: 32px 20px;
  }

  .doc-cards-wrapper {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .doc-card {
    padding: 20px 16px 64px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .section-header-right {
    width: 100%;
    justify-content: space-between;
  }

  .donut-wrapper {
    flex-direction: column;
    gap: 16px;
  }
}

@media (max-width: 480px) {
  .doc-card-info {
    gap: 10px;
  }

  .doc-info-item {
    font-size: 11px;
  }
}
</style>

<style>
.el-select-dropdown__item.is-selected {
  color: var(--color-secondary, #7C3AED);
  font-weight: 600;
}
</style>