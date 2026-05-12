<template>
  <div class="documents-page">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon :size="24"><FolderOpened /></el-icon>
        知识库文档管理
      </h1>
      <p class="page-desc">上传、管理和检索知识库文档，支持 PDF、Word、HTML、TXT 格式</p>
    </div>

    <div class="search-section">
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="输入文档名搜索..."
          clearable
          size="large"
          @keyup.enter="handleSearch"
          @clear="handleClearSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button class="search-btn" size="large" @click="handleSearch">
          搜索
        </el-button>
      </div>
    </div>

    <div class="upload-zone"
      :class="{ 'is-dragover': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="fileInputRef"
        type="file"
        accept=".pdf,.docx,.doc,.html,.htm,.txt"
        multiple
        style="display: none"
        @change="handleFileSelect"
      />
      <div class="upload-content" @click="fileInputRef?.click()">
        <el-icon :size="48" class="upload-icon"><UploadFilled /></el-icon>
        <p class="upload-text">点击或拖拽文件到此处上传</p>
        <p class="upload-hint">支持 PDF、Word (.docx/.doc)、HTML、TXT，单文件最大 50MB</p>
      </div>
    </div>

    <div class="upload-notice">
      <el-icon :size="16"><InfoFilled /></el-icon>
      <span>上传文档后需经过解析、分块、向量化等处理步骤，请耐心等待</span>
    </div>

    <div v-if="uploadingFiles.length > 0" class="upload-progress-section">
      <div v-for="uf in uploadingFiles" :key="uf.name" class="upload-progress-item">
        <div class="upload-progress-info">
          <el-icon><Document /></el-icon>
          <span class="upload-progress-name">{{ uf.name }}</span>
          <el-tag v-if="uf.status === 'uploading'" type="warning" size="small">处理中</el-tag>
          <el-tag v-else type="success" size="small">完成</el-tag>
        </div>
        <div v-if="uf.status === 'uploading'" class="upload-progress-bar">
          <div class="upload-progress-fill"></div>
        </div>
      </div>
    </div>

    <div class="documents-section">
      <div class="section-header">
        <h3>
          <template v-if="isSearching">搜索结果：{{ total }} 个文档</template>
          <template v-else>文档列表（{{ total }}）</template>
        </h3>
        <el-button text :loading="loading" @click="loadDocuments">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="documents"
        stripe
        style="width: 100%"
        empty-text="暂无文档，请上传"
        @row-click="handleRowClick"
        highlight-current-row
      >
        <el-table-column prop="original_filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <div class="file-type-cell">
              <el-icon :size="18" :color="getFileTypeColor(row.file_type)">
                <component :is="getFileTypeIcon(row.file_type)" />
              </el-icon>
              <span :style="{ color: getFileTypeColor(row.file_type) }" class="file-type-text">
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
            <el-popconfirm
              title="确定删除该文档？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm.stop="handleDelete(row.id)"
            >
              <template #reference>
                <el-button type="danger" text size="small" @click.stop>
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="chunkDialogVisible"
      :title="chunkDialogTitle"
      width="800px"
      destroy-on-close
    >
      <div v-loading="chunkLoading" class="chunk-list">
        <div v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  FolderOpened, UploadFilled, Document, Delete, Refresh, Search, InfoFilled
} from '@element-plus/icons-vue'
import { getDocumentsApi, deleteDocumentApi, getDocumentChunksApi, uploadDocumentApi } from '@/api/documents'
import type { DocumentInfo, ChunkInfo } from '@/types'

const fileInputRef = ref<HTMLInputElement>()
const isDragOver = ref(false)
const loading = ref(false)
const chunkLoading = ref(false)
const documents = ref<DocumentInfo[]>([])
const total = ref(0)
const chunks = ref<ChunkInfo[]>([])
const chunkDialogVisible = ref(false)
const chunkDialogTitle = ref('')

const searchQuery = ref('')
const isSearching = ref(false)

interface UploadingFile {
  name: string
  status: 'uploading' | 'success' | 'error'
  error?: string
}

const uploadingFiles = ref<UploadingFile[]>([])

const currentPage = ref(1)
const pageSize = ref(10)

function getFileTypeIcon(fileType: string): string {
  const map: Record<string, string> = {
    pdf: 'PictureFilled',
    docx: 'Document',
    doc: 'Document',
    html: 'Monitor',
    htm: 'Monitor',
    txt: 'Memo',
  }
  return map[fileType.toLowerCase()] || 'Document'
}

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

async function loadDocuments(search?: string) {
  loading.value = true
  try {
    const offset = (currentPage.value - 1) * pageSize.value
    const res = await getDocumentsApi(pageSize.value, offset, search)
    documents.value = res.items
    total.value = res.total
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function uploadFile(file: File) {
  const uf: UploadingFile = { name: file.name, status: 'uploading' }
  uploadingFiles.value.push(uf)

  try {
    await uploadDocumentApi(file)
    uf.status = 'success'
    ElMessage.success(`"${file.name}" 上传并处理成功`)
    currentPage.value = 1
    await loadDocuments()
  } catch (e: unknown) {
    const errMsg = (e as { message?: string })?.message || '处理失败'
    ElMessage.error(`"${file.name}" 上传失败: ${errMsg}，请重试`)
    uploadingFiles.value = uploadingFiles.value.filter(f => f.name !== uf.name)
    return
  }

  setTimeout(() => {
    uploadingFiles.value = uploadingFiles.value.filter(f => f.name !== uf.name)
  }, 3000)
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (!files) return
  for (let i = 0; i < files.length; i++) {
    uploadFile(files[i])
  }
}

function handleFileSelect() {
  const files = fileInputRef.value?.files
  if (!files) return
  for (let i = 0; i < files.length; i++) {
    uploadFile(files[i])
  }
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function handleDelete(id: string) {
  try {
    await deleteDocumentApi(id)
    ElMessage.success('文档已删除')
    if (documents.value.length === 1 && currentPage.value > 1) {
      currentPage.value--
    }
    await loadDocuments(isSearching.value ? searchQuery.value.trim() : undefined)
  } catch (e: unknown) {
    const msg = (e as { message?: string })?.message || '删除失败'
    ElMessage.error(msg)
  }
}

async function handleRowClick(row: DocumentInfo) {
  chunkDialogTitle.value = `${row.original_filename} - 分块详情`
  chunkDialogVisible.value = true
  chunkLoading.value = true
  try {
    const res = await getDocumentChunksApi(row.id)
    chunks.value = res.chunks
  } catch {
    chunks.value = []
  } finally {
    chunkLoading.value = false
  }
}

async function handleSearch() {
  const q = searchQuery.value.trim()
  if (q) {
    isSearching.value = true
    currentPage.value = 1
    await loadDocuments(q)
  }
}

async function handleClearSearch() {
  searchQuery.value = ''
  isSearching.value = false
  currentPage.value = 1
  await loadDocuments()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadDocuments(isSearching.value ? searchQuery.value.trim() : undefined)
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadDocuments(isSearching.value ? searchQuery.value.trim() : undefined)
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.documents-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
  height: 100vh;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 8px;
}

.page-desc {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
}

.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #f8fafc;
  margin-bottom: 24px;
}

.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.04);
}

.upload-icon {
  color: #cbd5e1;
  margin-bottom: 12px;
}

.upload-zone:hover .upload-icon,
.upload-zone.is-dragover .upload-icon {
  color: #6366f1;
}

.upload-text {
  font-size: 16px;
  color: #475569;
  margin: 0 0 6px;
}

.upload-hint {
  font-size: 12px;
  color: #94a3b8;
  margin: 0;
}

.upload-notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 24px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #fff7e6, #fff3d6);
  border: 1px solid #ffd666;
  border-radius: 8px;
  font-size: 13px;
  color: #d48806;
  font-weight: 500;
}

.upload-progress-section {
  margin-bottom: 24px;
}

.upload-progress-item {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
}

.upload-progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.upload-progress-name {
  flex: 1;
  font-size: 14px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-progress-bar {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.upload-progress-fill {
  height: 100%;
  width: 30%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 2px;
  animation: progress 1.8s ease-in-out infinite;
}

@keyframes progress {
  0% { width: 10%; }
  50% { width: 70%; }
  100% { width: 90%; }
}

.upload-progress-error {
  color: #f56c6c;
  font-size: 12px;
  margin: 6px 0 0;
}

.documents-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.documents-section :deep(.el-table__body-wrapper) {
  border-radius: 0 0 8px 8px;
}

.documents-section :deep(.el-table__body tr) {
  cursor: pointer;
  transition: box-shadow 0.25s ease, background-color 0.25s ease;
}

.documents-section :deep(.el-table__body tr:hover) {
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.12);
}

.documents-section :deep(.el-table__body tr:hover > td) {
  background-color: rgba(99, 102, 241, 0.04) !important;
}

.chunk-list {
  max-height: 500px;
  overflow-y: auto;
  padding: 0 4px;
}

.chunk-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.chunk-item:hover {
  border-color: #6366f1;
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.chunk-title {
  font-size: 13px;
  color: #94a3b8;
}

.chunk-content {
  font-size: 14px;
  color: #1e293b;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
}

.search-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 24px;
}

.search-bar {
  display: flex;
  gap: 12px;
}

.search-bar .el-input {
  flex: 1;
}

.search-btn {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 500;
  border-radius: 8px;
  transition: opacity 0.2s;
  min-width: 72px;
}

.search-btn:hover {
  opacity: 0.9;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 4px;
}

.file-type-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.file-type-text {
  font-size: 13px;
  font-weight: 600;
}
</style>
