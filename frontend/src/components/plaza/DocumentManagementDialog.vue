<template>
  <el-dialog
    v-model="visible"
    :title="`${kbName} - 文档管理`"
    width="780px"
    :close-on-click-modal="false"
    destroy-on-close
    @closed="handleClosed"
  >
    <div v-loading="loading" class="doc-mgmt-body">
      <div v-if="documents.length > 0" class="doc-list">
        <div
          v-for="doc in documents"
          :key="doc.id"
          class="doc-item"
        >
          <div class="doc-item-left">
            <div class="doc-item-icon" :class="getIconClass(doc.file_type)">
              <el-icon :size="20"><Document /></el-icon>
            </div>
            <div class="doc-item-info">
              <div class="doc-item-name" :title="doc.original_filename || doc.filename">
                {{ doc.original_filename || doc.filename }}
              </div>
              <div class="doc-item-meta">
                <span class="doc-item-meta-item">{{ formatFileType(doc.file_type) }}</span>
                <span class="doc-item-meta-item">{{ formatFileSize(doc.file_size) }}</span>
                <span class="doc-item-meta-item">{{ doc.chunk_count }} 个片段</span>
                <el-tag
                  :type="statusTagType(doc.status)"
                  size="small"
                  class="doc-status-tag"
                >
                  {{ statusLabel(doc.status) }}
                </el-tag>
              </div>
              <div class="doc-item-time">{{ formatDate(doc.created_at) }}</div>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else-if="!loading" description="暂无文档" :image-size="80" />
    </div>

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
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { getKbDocumentsApi } from '@/api/knowledgeBases'
import type { DocumentInfo } from '@/types'

interface Props {
  modelValue: boolean
  kbId: string
  kbName: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const visible = ref(false)
const loading = ref(false)
const documents = ref<DocumentInfo[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    currentPage.value = 1
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
      (currentPage.value - 1) * pageSize.value
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

function handleClosed() {
  documents.value = []
  total.value = 0
  currentPage.value = 1
}

function getIconClass(fileType: string): string {
  const iconMap: Record<string, string> = {
    pdf: 'icon-pdf',
    doc: 'icon-word',
    docx: 'icon-word',
    txt: 'icon-txt',
    md: 'icon-md',
    xlsx: 'icon-excel',
    xls: 'icon-excel',
    ppt: 'icon-ppt',
    pptx: 'icon-ppt',
    csv: 'icon-csv'
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
    completed: 'success',
    processing: 'warning',
    pending: 'info',
    failed: 'danger'
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    completed: '已完成',
    processing: '处理中',
    pending: '待处理',
    failed: '失败'
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
}

.doc-item:hover {
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
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 2px;
}

.doc-item-meta-item {
  font-size: 12px;
  color: var(--color-text-muted);
}

.doc-status-tag {
  font-size: 11px;
}

.doc-item-time {
  font-size: 11px;
  color: var(--color-text-subtle);
}

.doc-mgmt-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 8px;
}
</style>