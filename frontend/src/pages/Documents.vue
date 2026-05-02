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
          placeholder="输入关键词搜索知识库内容..."
          clearable
          size="large"
          @keyup.enter="handleSearch"
          @clear="searchResults = []"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button class="search-btn" size="large" :loading="searchLoading" @click="handleSearch">
          搜索
        </el-button>
      </div>
      <div v-if="searchResults.length > 0" class="search-results">
        <div class="search-results-header">
          <span>找到 {{ searchResults.length }} 条相关结果</span>
          <el-button text size="small" @click="searchResults = []; searchQuery = ''">清除</el-button>
        </div>
        <div v-for="(item, idx) in searchResults" :key="idx" class="search-result-item">
          <div class="search-result-header">
            <span class="search-result-title">{{ item.title }}</span>
            <el-tag size="small" type="info">相似度 {{ (item.score * 100).toFixed(0) }}%</el-tag>
          </div>
          <p class="search-result-source">
            <el-icon :size="14"><Document /></el-icon>
            {{ item.source }}
          </p>
          <p class="search-result-content">{{ item.content.slice(0, 300) }}{{ item.content.length > 300 ? '...' : '' }}</p>
        </div>
      </div>
      <el-empty v-if="searched && searchResults.length === 0 && !searchLoading" description="未找到相关内容" />
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

    <div v-if="uploadingFiles.length > 0" class="upload-progress-section">
      <div v-for="uf in uploadingFiles" :key="uf.name" class="upload-progress-item">
        <div class="upload-progress-info">
          <el-icon><Document /></el-icon>
          <span class="upload-progress-name">{{ uf.name }}</span>
          <el-tag v-if="uf.status === 'uploading'" type="warning" size="small">处理中</el-tag>
          <el-tag v-else-if="uf.status === 'success'" type="success" size="small">完成</el-tag>
          <el-tag v-else type="danger" size="small">失败</el-tag>
        </div>
        <div v-if="uf.status === 'uploading'" class="upload-progress-bar">
          <div class="upload-progress-fill"></div>
        </div>
        <p v-if="uf.error" class="upload-progress-error">{{ uf.error }}</p>
      </div>
    </div>

    <div class="documents-section">
      <div class="section-header">
        <h3>文档列表（{{ total }}）</h3>
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
        <el-table-column prop="file_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="80" align="center" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'completed'" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="row.status === 'processing'" type="warning" size="small">处理中</el-tag>
            <el-tooltip v-else :content="row.error_message" placement="top">
              <el-tag type="danger" size="small">失败</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  FolderOpened, UploadFilled, Document, Delete, Refresh, Search
} from '@element-plus/icons-vue'
import { getDocumentsApi, deleteDocumentApi, getDocumentChunksApi, uploadDocumentApi, searchDocumentsApi } from '@/api/documents'
import type { DocumentInfo, ChunkInfo, SearchResult } from '@/types'

const fileInputRef = ref<HTMLInputElement>()
const isDragOver = ref(false)
const loading = ref(false)
const chunkLoading = ref(false)
const searchLoading = ref(false)
const documents = ref<DocumentInfo[]>([])
const total = ref(0)
const chunks = ref<ChunkInfo[]>([])
const chunkDialogVisible = ref(false)
const chunkDialogTitle = ref('')

const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searched = ref(false)

interface UploadingFile {
  name: string
  status: 'uploading' | 'success' | 'error'
  error?: string
}

const uploadingFiles = ref<UploadingFile[]>([])

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

async function loadDocuments() {
  loading.value = true
  try {
    const res = await getDocumentsApi(200, 0)
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
    await loadDocuments()
  } catch (e: unknown) {
    uf.status = 'error'
    uf.error = (e as { message?: string })?.message || '处理失败'
    ElMessage.error(`"${file.name}" 处理失败: ${uf.error}`)
  } finally {
    setTimeout(() => {
      uploadingFiles.value = uploadingFiles.value.filter(f => f.name !== uf.name)
    }, 3000)
  }
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
    documents.value = documents.value.filter(d => d.id !== id)
    total.value--
    ElMessage.success('文档已删除')
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
  if (!q) return
  searchLoading.value = true
  searched.value = true
  try {
    const res = await searchDocumentsApi(q, 10)
    searchResults.value = res.results
  } catch {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
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
  color: #303133;
  margin: 0 0 8px;
}

.page-desc {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.upload-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #fafafa;
  margin-bottom: 24px;
}

.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.04);
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 12px;
}

.upload-zone:hover .upload-icon,
.upload-zone.is-dragover .upload-icon {
  color: #ff6b35;
}

.upload-text {
  font-size: 16px;
  color: #606266;
  margin: 0 0 6px;
}

.upload-hint {
  font-size: 12px;
  color: #c0c4cc;
  margin: 0;
}

.upload-progress-section {
  margin-bottom: 24px;
}

.upload-progress-item {
  background: #fff;
  border: 1px solid #ebeef5;
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
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-progress-bar {
  height: 4px;
  background: #ebeef5;
  border-radius: 2px;
  overflow: hidden;
}

.upload-progress-fill {
  height: 100%;
  width: 30%;
  background: linear-gradient(90deg, #ff6b35, #f7931e);
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
  color: #303133;
  margin: 0;
}

.chunk-list {
  max-height: 500px;
  overflow-y: auto;
  padding: 0 4px;
}

.chunk-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.chunk-item:hover {
  border-color: #ff6b35;
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.chunk-title {
  font-size: 13px;
  color: #909399;
}

.chunk-content {
  font-size: 14px;
  color: #303133;
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
  background: linear-gradient(135deg, #ff6b35, #f7931e) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 500;
  border-radius: 8px;
  transition: opacity 0.2s;
}

.search-btn:hover {
  opacity: 0.9;
}

.search-results {
  margin-top: 20px;
}

.search-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  font-size: 14px;
  color: #606266;
}

.search-result-item {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.search-result-item:hover {
  border-color: #ff6b35;
}

.search-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.search-result-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.search-result-source {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  margin: 0 0 8px;
}

.search-result-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
  margin: 0;
  white-space: pre-wrap;
}
</style>
