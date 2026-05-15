import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDocumentsApi, deleteDocumentApi, deleteDocumentsBatchApi, getDocumentChunksApi, uploadDocumentApi } from '@/api/documents'
import type { DocumentInfo, ChunkInfo } from '@/types'

interface UploadingFile {
  name: string
  status: 'uploading' | 'success' | 'error'
  error?: string
}

export function useDocuments() {
  const loading = ref(false)
  const chunkLoading = ref(false)
  const documents = ref<DocumentInfo[]>([])
  const total = ref(0)
  const chunks = ref<ChunkInfo[]>([])
  const chunkDialogVisible = ref(false)
  const chunkDialogTitle = ref('')
  const uploadingFiles = ref<UploadingFile[]>([])

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

  async function uploadFile(file: File, pageSize: number, currentPage: number) {
    const uf: UploadingFile = { name: file.name, status: 'uploading' }
    uploadingFiles.value.push(uf)

    try {
      await uploadDocumentApi(file)
      uf.status = 'success'
      ElMessage.success(`"${file.name}" 上传并处理成功`)
      await loadDocuments(pageSize, 1)
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

  async function deleteDocument(id: string, pageSize: number, currentPage: number, isSearching: boolean, searchQuery?: string) {
    try {
      await deleteDocumentApi(id)
      ElMessage.success('文档已删除')
      if (documents.value.length === 1 && currentPage > 1) {
        currentPage -= 1
      }
      await loadDocuments(pageSize, currentPage, isSearching ? searchQuery : undefined)
    } catch (e: unknown) {
      const msg = (e as { message?: string })?.message || '删除失败'
      ElMessage.error(msg)
    }
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

  async function deleteDocumentsBatch(ids: string[], pageSize: number, currentPage: number, isSearching: boolean, searchQuery?: string) {
    try {
      const res = await deleteDocumentsBatchApi(ids)
      ElMessage.success(res.deleted_count > 0 ? `已删除 ${res.deleted_count} 个文档` : '没有文档被删除')
      const remaining = documents.value.length - ids.length
      if (remaining <= 0 && currentPage > 1) {
        currentPage -= 1
      }
      await loadDocuments(pageSize, currentPage, isSearching ? searchQuery : undefined)
    } catch (e: unknown) {
      const msg = (e as { message?: string })?.message || '批量删除失败'
      ElMessage.error(msg)
    }
  }

  return {
    loading,
    chunkLoading,
    documents,
    total,
    chunks,
    chunkDialogVisible,
    chunkDialogTitle,
    uploadingFiles,
    loadDocuments,
    uploadFile,
    deleteDocument,
    deleteDocumentsBatch,
    loadDocumentChunks,
    refresh
  }
}