import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDocumentsApi, deleteDocumentApi, deleteDocumentsBatchApi, getDocumentChunksApi, uploadDocumentApi } from '@/api/documents'
import type { DocumentInfo, ChunkInfo } from '@/types'

interface UploadingFile {
  name: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
}

const MAX_CONCURRENT_UPLOADS = 1

export const uploadingFiles = ref<UploadingFile[]>([])
export const uploadProgressCollapsed = ref(false)
export const uploadProgressPage = ref(1)
export const uploadProgressPageSize = ref(5)

export const uploadStats = computed(() => {
  const total = uploadingFiles.value.length
  const pending = uploadingFiles.value.filter(f => f.status === 'pending').length
  const uploading = uploadingFiles.value.filter(f => f.status === 'uploading').length
  const completed = uploadingFiles.value.filter(f => f.status === 'success').length
  const failed = uploadingFiles.value.filter(f => f.status === 'error').length
  const active = pending + uploading
  const allDone = total > 0 && active === 0
  return { total, pending, uploading, completed, failed, active, allDone }
})

export const activeUploadingFiles = computed(() =>
  uploadingFiles.value.filter(f => f.status === 'pending' || f.status === 'uploading')
)

export const pagedUploadingFiles = computed(() => {
  const start = (uploadProgressPage.value - 1) * uploadProgressPageSize.value
  return activeUploadingFiles.value.slice(start, start + uploadProgressPageSize.value)
})

export function removeUploadRecord(name: string) {
  uploadingFiles.value = uploadingFiles.value.filter(f => f.name !== name)
}

export function clearCompletedUploads() {
  uploadingFiles.value = uploadingFiles.value.filter(
    f => f.status === 'pending' || f.status === 'uploading'
  )
  uploadProgressPage.value = 1
  uploadProgressCollapsed.value = false
}

let _onUploadSuccess: (() => Promise<void>) | null = null

export function setOnUploadSuccess(cb: (() => Promise<void>) | null) {
  _onUploadSuccess = cb
}

export function useUploadLifecycle(refreshFn: () => Promise<void>) {
  onMounted(() => {
    setOnUploadSuccess(refreshFn)
  })
  onUnmounted(() => {
    setOnUploadSuccess(null)
  })
}

async function uploadFile(file: File, uf: UploadingFile) {
  uf.status = 'uploading'
  uploadProgressCollapsed.value = false

  try {
    await uploadDocumentApi(file)
    uf.status = 'success'
    if (_onUploadSuccess) {
      await _onUploadSuccess()
    }
  } catch (e: unknown) {
    const errMsg = (e as { message?: string })?.message || '处理失败'
    console.error(`[文档上传失败] "${file.name}":`, errMsg)
    uf.status = 'error'
    uf.error = errMsg
    if (errMsg.includes('已上传过') || errMsg.includes('重复上传')) {
      ElMessage.warning(`"${file.name}" 已上传过，无需重复上传`)
    } else {
      ElMessage.error(`"${file.name}" 上传失败`)
    }
  }

  if (uploadStats.value.allDone) {
    setTimeout(() => {
      uploadProgressCollapsed.value = true
    }, 5000)
  }
}

export async function uploadFiles(files: File[]) {
  const startIdx = uploadingFiles.value.length
  const items = files.map(f => ({
    name: f.name,
    status: 'pending' as const,
  }))
  uploadingFiles.value.push(...items)
  uploadProgressCollapsed.value = false
  uploadProgressPage.value = 1

  for (let i = 0; i < files.length; i += MAX_CONCURRENT_UPLOADS) {
    const batchFiles = files.slice(i, i + MAX_CONCURRENT_UPLOADS)
    const batchItems = uploadingFiles.value.slice(startIdx + i, startIdx + i + MAX_CONCURRENT_UPLOADS)
    await Promise.all(
      batchFiles.map((f, idx) => uploadFile(f, batchItems[idx]))
    )
  }
}

export function useDocuments() {
  const loading = ref(false)
  const chunkLoading = ref(false)
  const deletingIds = ref<Set<string>>(new Set())
  const documents = ref<DocumentInfo[]>([])
  const total = ref(0)
  const chunks = ref<ChunkInfo[]>([])
  const chunkDialogVisible = ref(false)
  const chunkDialogTitle = ref('')

  async function loadDocuments(pageSize: number, currentPage: number, search?: string) {
    loading.value = true
    try {
      const offset = (currentPage - 1) * pageSize
      const res = await getDocumentsApi(pageSize, offset, search)
      documents.value = res.items
      total.value = res.total
    } catch {
      // ignore
    } finally {
      loading.value = false
    }
  }

  async function deleteDocument(id: string, pageSize: number, currentPage: number, isSearching: boolean, searchQuery?: string): Promise<number> {
    const snapshot = documents.value
    const prevTotal = total.value
    let adjustedPage = currentPage
    deletingIds.value = new Set(deletingIds.value).add(id)
    documents.value = documents.value.filter(d => d.id !== id)
    total.value = total.value - 1

    try {
      await deleteDocumentApi(id)
      ElMessage.success('文档已删除')
      if (documents.value.length === 0 && currentPage > 1) {
        adjustedPage = currentPage - 1
      }
    } catch (e: unknown) {
      documents.value = snapshot
      total.value = prevTotal
      adjustedPage = currentPage
    } finally {
      const next = new Set(deletingIds.value)
      next.delete(id)
      deletingIds.value = next
      await loadDocuments(pageSize, adjustedPage, isSearching ? searchQuery : undefined)
    }
    return adjustedPage
  }

  async function loadDocumentChunks(doc: DocumentInfo) {
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

  async function refresh(pageSize: number, currentPage: number, isSearching: boolean, searchQuery?: string) {
    await loadDocuments(pageSize, currentPage, isSearching ? searchQuery : undefined)
  }

  async function deleteDocumentsBatch(ids: string[], pageSize: number, currentPage: number, isSearching: boolean, searchQuery?: string): Promise<number> {
    const snapshot = documents.value
    const prevTotal = total.value
    let adjustedPage = currentPage
    const idsSet = new Set(ids)
    deletingIds.value = new Set([...deletingIds.value, ...ids])
    documents.value = documents.value.filter(d => !idsSet.has(d.id))
    total.value = Math.max(0, total.value - ids.length)

    try {
      const res = await deleteDocumentsBatchApi(ids)
      ElMessage.success(res.deleted_count > 0 ? `已删除 ${res.deleted_count} 个文档` : '没有文档被删除')
      if (documents.value.length === 0 && currentPage > 1) {
        adjustedPage = currentPage - 1
      }
    } catch (e: unknown) {
      documents.value = snapshot
      total.value = prevTotal
      adjustedPage = currentPage
    } finally {
      const next = new Set(deletingIds.value)
      for (const id of ids) {
        next.delete(id)
      }
      deletingIds.value = next
      await loadDocuments(pageSize, adjustedPage, isSearching ? searchQuery : undefined)
    }
    return adjustedPage
  }

  return {
    loading,
    chunkLoading,
    deletingIds,
    documents,
    total,
    chunks,
    chunkDialogVisible,
    chunkDialogTitle,
    loadDocuments,
    deleteDocument,
    deleteDocumentsBatch,
    loadDocumentChunks,
    refresh,
  }
}