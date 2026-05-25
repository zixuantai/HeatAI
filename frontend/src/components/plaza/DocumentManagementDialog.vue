<template>
  <el-dialog
    v-model="visible"
    :title="`${kbName} - 文档管理`"
    width="860px"
    :close-on-click-modal="false"
    :close-on-press-escape="!busy"
    :show-close="!busy"
    destroy-on-close
    @closed="handleClosed"
  >
    <!-- 搜索 + 上传 -->
    <div class="doc-toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索文档名..."
        clearable
        size="default"
        class="doc-search-input"
        @keyup.enter="handleSearch"
        @clear="handleClearSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <div class="doc-toolbar-spacer" />
      <el-button v-if="!batchMode" type="primary" @click="enterBatchMode" :disabled="uploading">
        <el-icon><Delete /></el-icon>
        批量删除
      </el-button>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        multiple
        :limit="10"
        accept=".pdf,.docx,.doc,.html,.htm,.txt,.md,.markdown,.csv,.json,.xlsx,.xls,.pptx,.ppt,.epub,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
        class="doc-upload-inline"
      >
        <el-button type="primary" :loading="uploading" :disabled="batchMode">
          <el-icon><Upload /></el-icon>
          上传文档
        </el-button>
      </el-upload>
    </div>

    <!-- 上传提示 -->
    <div v-if="uploadingFiles.length > 0" class="upload-progress-bar-outer">
      <div v-for="(uf, idx) in uploadingFiles" :key="idx" class="upload-progress-item">
        <el-icon :class="{ 'is-error': uf.status === 'error', 'is-success': uf.status === 'success' }">
          <component :is="uf.status === 'success' ? 'CircleCheck' : uf.status === 'error' ? 'CircleClose' : uf.status === 'uploading' ? 'Loading' : 'Clock'" />
        </el-icon>
        <span class="upload-progress-name">{{ uf.name }}</span>
        <el-tag v-if="uf.status === 'pending'" type="info" size="small">排队</el-tag>
        <el-tag v-else-if="uf.status === 'uploading'" type="warning" size="small">处理中</el-tag>
        <el-tag v-else-if="uf.status === 'success'" type="success" size="small">完成</el-tag>
        <el-tag v-else type="danger" size="small">{{ uf.error || '失败' }}</el-tag>
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
          >全选本页</el-checkbox>
          <el-checkbox
            :model-value="selectAllKB"
            :indeterminate="isIndeterminateKB"
            :disabled="allKbIdsLoading"
            size="large"
            @change="toggleSelectAllKB"
          >全选知识库</el-checkbox>
        </span>
        <span class="batch-selected-count">已选 <strong>{{ selectedIds.size }}</strong> 项</span>
      </div>
      <div class="batch-action-right">
        <button
          class="neu-btn-danger"
          :disabled="selectedIds.size === 0"
          @click="handleBatchRemove"
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

    <!-- 文档列表 -->
    <div v-loading="loading" class="doc-mgmt-body">
      <div v-if="documents.length > 0" class="doc-list">
        <div
          v-for="doc in documents"
          :key="doc.id"
          class="doc-item"
          :class="{ 'is-selected': batchMode && selectedIds.has(doc.id) }"
          @click="handleRowClick(doc)"
        >
          <div v-if="batchMode" class="doc-item-check" @click.stop="toggleSelect(doc)">
            <el-checkbox :model-value="selectedIds.has(doc.id)" />
          </div>
          <div class="doc-item-left">
            <div class="doc-item-icon" :class="getIconClass(doc.file_type)">
              <el-icon :size="20"><Document /></el-icon>
            </div>
            <div class="doc-item-info">
              <div class="doc-item-name" :title="doc.original_filename || doc.filename">
                {{ doc.original_filename || doc.filename }}
              </div>
              <div class="doc-item-meta">
                <span>{{ formatFileType(doc.file_type) }}</span>
                <span>{{ formatFileSize(doc.file_size) }}</span>
                <span>{{ doc.chunk_count }} 个片段</span>
                <el-tag :type="statusTagType(doc.status)" size="small">{{ statusLabel(doc.status) }}</el-tag>
              </div>
              <div class="doc-item-time">{{ formatDate(doc.created_at) }}</div>
            </div>
          </div>
          <div v-if="!batchMode" class="doc-item-actions">
            <button
              class="neu-btn-delete"
              @click.stop="handleRemoveClick(doc)"
            >
              <el-icon :size="14"><Delete /></el-icon>
            </button>
          </div>
        </div>
      </div>
      <el-empty v-else-if="!loading" description="暂无文档" :image-size="80" />
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="doc-mgmt-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        small
        @current-change="loadDocuments"
      />
    </div>

    <template #footer>
      <el-button @click="visible = false" :disabled="busy">关闭</el-button>
    </template>

    <!-- 分块详情弹窗 -->
    <el-dialog
      v-model="chunkDialogVisible"
      :title="chunkDialogTitle"
      width="800px"
      destroy-on-close
      append-to-body
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

    <!-- 处理中遮罩 -->
    <div v-if="busy" class="processing-overlay">
      <div class="processing-dialog-inner">
        <el-icon class="processing-spinner" :size="40"><Loading /></el-icon>
        <p class="processing-text">正在处理，请耐心等待</p>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Search, Document, Delete, Upload, CircleCheck, CircleClose, Loading, Clock, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import {
  getKbDocumentsApi, getAllKbDocumentIdsApi, uploadDocumentToKbApi,
  removeDocumentFromKbApi, removeDocumentsFromKbBatchApi
} from '@/api/knowledgeBases'
import { getDocumentChunksApi } from '@/api/documents'
import type { DocumentInfo, ChunkInfo } from '@/types'

interface UploadingItem {
  name: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
}

interface Props {
  modelValue: boolean
  kbId: string
  kbName: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'updated'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const visible = ref(false)
const uploadRef = ref<any>()
const loading = ref(false)
const uploading = ref(false)
const busy = ref(false)
const documents = ref<DocumentInfo[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchQuery = ref('')
const isSearching = ref(false)

const chunks = ref<ChunkInfo[]>([])
const chunkDialogVisible = ref(false)
const chunkDialogTitle = ref('')
const chunkLoading = ref(false)

const uploadingFiles = ref<UploadingItem[]>([])

// batch mode
const batchMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const allKbIds = ref<string[]>([])
const allKbIdsLoading = ref(false)
const isPageAllSelected = ref(false)

const selectAllPage = computed(() => batchMode.value && documents.value.length > 0 && isPageAllSelected.value)
const isIndeterminatePage = computed(() =>
  batchMode.value && documents.value.some(d => selectedIds.value.has(d.id)) && !documents.value.every(d => selectedIds.value.has(d.id))
)
const selectAllKB = computed(() =>
  batchMode.value && allKbIds.value.length > 0 && allKbIds.value.every(id => selectedIds.value.has(id))
)
const isIndeterminateKB = computed(() =>
  batchMode.value && allKbIds.value.length > 0 && allKbIds.value.some(id => selectedIds.value.has(id)) && !allKbIds.value.every(id => selectedIds.value.has(id))
)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    currentPage.value = 1
    searchQuery.value = ''
    isSearching.value = false
    exitBatchMode()
    loadDocuments()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

async function loadDocuments() {
  loading.value = true
  try {
    const result = await getKbDocumentsApi(
      props.kbId,
      pageSize.value,
      (currentPage.value - 1) * pageSize.value,
      isSearching.value ? searchQuery.value.trim() : undefined
    )
    documents.value = result.items
    total.value = result.total
  } catch {
    documents.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function handleFileChange(file: UploadFile) {
  if (!file.raw) return
  const raw = file.raw

  const parts = raw.name.split('.')
  const ext = (parts.length > 1 ? parts.pop() : '')?.toLowerCase() || ''
  const supported = ['pdf','docx','doc','html','htm','txt','md','markdown','csv','json','xlsx','xls','pptx','ppt','epub','png','jpg','jpeg','bmp','tiff','webp']
  if (!supported.includes(ext)) {
    ElMessage.warning(`不支持的文件类型: .${ext}`)
    return
  }
  if (raw.size > 50 * 1024 * 1024) {
    ElMessage.warning('单个文件不能超过 50MB')
    return
  }

  const item: UploadingItem = { name: raw.name, status: 'pending' }
  uploadingFiles.value.push(item)
  uploading.value = true

  try {
    item.status = 'uploading'
    await uploadDocumentToKbApi(props.kbId, raw)
    item.status = 'success'
    ElMessage.success(`"${raw.name}" 上传成功`)
  } catch (e: any) {
    item.status = 'error'
    item.error = e.message || '上传失败'
    if (!(e.message || '').includes('已上传过') && !(e.message || '').includes('重复')) {
      ElMessage.error(`"${raw.name}" 上传失败`)
    }
  }

  // Check if all done
  const active = uploadingFiles.value.filter(f => f.status === 'pending' || f.status === 'uploading')
  if (active.length === 0) {
    uploading.value = false
    loading.value = true
    currentPage.value = 1
    isSearching.value = false
    searchQuery.value = ''
    exitBatchMode()
    await loadDocuments()
    loading.value = false
    emit('updated')
    setTimeout(() => { uploadingFiles.value = [] }, 3000)
  }
}

async function handleRemoveClick(doc: DocumentInfo) {
  try {
    await ElMessageBox.confirm(
      '确定要移除该文档吗？',
      '移除确认',
      { confirmButtonText: '移除', cancelButtonText: '取消', type: 'warning' }
    )
    busy.value = true
    await removeDocumentFromKbApi(props.kbId, doc.id)
    ElMessage.success('文档已移除')
    if (documents.value.length <= 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    await loadDocuments()
    emit('updated')
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.message || '移除失败')
    }
  } finally {
    busy.value = false
  }
}

async function handleRowClick(doc: DocumentInfo) {
  if (batchMode.value) {
    toggleSelect(doc)
    return
  }
  chunkDialogTitle.value = `${doc.original_filename} - 分块详情`
  chunkDialogVisible.value = true
  chunkLoading.value = true
  try {
    const res = await getDocumentChunksApi(doc.id)
    chunks.value = res.chunks
  } catch {
    chunks.value = []
  } finally {
    chunkLoading.value = false
  }
}

async function handleSearch() {
  const q = searchQuery.value.trim()
  isSearching.value = !!q
  currentPage.value = 1
  exitBatchMode()
  await loadDocuments()
}

async function handleClearSearch() {
  searchQuery.value = ''
  isSearching.value = false
  currentPage.value = 1
  exitBatchMode()
  await loadDocuments()
}

// Batch operations
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
      const res = await getAllKbDocumentIdsApi(props.kbId, isSearching.value ? searchQuery.value.trim() : undefined)
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

async function handleBatchRemove() {
  if (selectedIds.value.size === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要移除选中的 ${selectedIds.value.size} 个文档吗？`,
      '批量移除确认',
      { confirmButtonText: '移除', cancelButtonText: '取消', type: 'warning' }
    )
    const ids = Array.from(selectedIds.value)
    exitBatchMode()
    busy.value = true
    const res = await removeDocumentsFromKbBatchApi(props.kbId, ids)
    ElMessage.success(`已移除 ${res.removed_count} 个文档`)
    if (documents.value.length <= ids.length && currentPage.value > 1) {
      currentPage.value -= 1
    }
    await loadDocuments()
    emit('updated')
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.message || '移除失败')
    }
  } finally {
    busy.value = false
  }
}

function handleClosed() {
  documents.value = []
  total.value = 0
  currentPage.value = 1
  searchQuery.value = ''
  isSearching.value = false
  chunks.value = []
  uploadingFiles.value = []
  uploadRef.value?.clearFiles()
}

function getIconClass(fileType: string): string {
  const iconMap: Record<string, string> = {
    pdf: 'icon-pdf', doc: 'icon-word', docx: 'icon-word',
    txt: 'icon-txt', md: 'icon-md', xlsx: 'icon-excel', xls: 'icon-excel',
    ppt: 'icon-ppt', pptx: 'icon-ppt', csv: 'icon-csv'
  }
  return iconMap[fileType] || 'icon-default'
}

function formatFileType(type: string): string {
  if (!type) return '-'
  return type.toUpperCase()
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function statusTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    completed: 'success', processing: 'warning', pending: 'info', failed: 'danger'
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    completed: '已完成', processing: '处理中', pending: '待处理', failed: '失败'
  }
  return map[status] || status
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.doc-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.doc-search-input {
  width: 220px;
}

.doc-toolbar-spacer {
  flex: 1;
}

.doc-upload-inline :deep(.el-upload) {
  display: inline-flex;
  align-items: center;
  margin-top: 9px;
}

.upload-progress-bar-outer {
  margin-bottom: 12px;
  max-height: 150px;
  overflow-y: auto;
}

.upload-progress-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: 13px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  margin-bottom: 4px;
  background: var(--color-bg);
}

.upload-progress-item .el-icon.is-error { color: #ef4444; }
.upload-progress-item .el-icon.is-success { color: #22c55e; }

.upload-progress-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: var(--font-weight-medium);
}

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

.neu-btn-danger:hover {
  box-shadow:
    4px 4px 12px rgba(239, 68, 68, 0.28),
    -4px -4px 12px rgba(255, 255, 255, 0.8);
  transform: translateY(-1px);
}

.neu-btn-danger:active {
  transform: translateY(2px);
  box-shadow:
    inset 3px 3px 6px rgba(0, 0, 0, 0.15),
    inset -3px -3px 6px rgba(255, 255, 255, 0.6);
}

.neu-btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.doc-mgmt-body {
  min-height: 200px;
  max-height: 420px;
  overflow-y: auto;
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-item {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  transition: border-color var(--transition-fast);
  cursor: pointer;
}

.doc-item:hover {
  border-color: var(--color-primary);
}

.doc-item.is-selected {
  border-color: var(--color-secondary, #7C3AED);
  background: rgba(124, 58, 237, 0.04);
}

.doc-item-check {
  margin-right: 10px;
}

.doc-item-check :deep(.el-checkbox__input.is-checked .el-checkbox__inner),
.doc-item-check :deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: var(--color-secondary);
  border-color: var(--color-secondary);
}

.doc-item-check :deep(.el-checkbox__input.is-checked:hover .el-checkbox__inner),
.doc-item-check :deep(.el-checkbox__input.is-indeterminate:hover .el-checkbox__inner) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

.doc-item-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.doc-item-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--gradient-subtle);
  color: var(--color-primary);
}

.doc-item-icon.icon-pdf { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.doc-item-icon.icon-word { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.doc-item-icon.icon-txt { background: rgba(107, 114, 128, 0.1); color: #6b7280; }
.doc-item-icon.icon-md { background: rgba(79, 70, 229, 0.1); color: #4f46e5; }
.doc-item-icon.icon-excel { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.doc-item-icon.icon-ppt { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
.doc-item-icon.icon-csv { background: rgba(14, 165, 233, 0.1); color: #0ea5e9; }

.doc-item-info {
  flex: 1;
  min-width: 0;
}

.doc-item-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.doc-item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 2px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.doc-item-time {
  font-size: 11px;
  color: var(--color-text-subtle);
}

.doc-item-actions {
  margin-left: 8px;
  flex-shrink: 0;
}

.neu-btn-delete {
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

.doc-mgmt-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 8px;
}

.chunk-list {
  max-height: 500px;
  overflow-y: auto;
}

.chunk-item {
  padding: 16px 18px;
  margin-bottom: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.chunk-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.chunk-content {
  font-size: var(--font-size-base);
  color: var(--color-text-main);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
}

.processing-dialog-inner {
  text-align: center;
  padding: 40px;
}

.processing-spinner {
  color: var(--color-primary);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.processing-text {
  margin-top: 16px;
  font-size: 15px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
}
</style>
