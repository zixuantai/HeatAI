import { request } from '@/utils/request'
import type { DocumentInfo, DocumentListResponse, DocumentChunksResponse, SearchResponse, DocumentStats } from '@/types'

export function getDocumentStatsApi(): Promise<DocumentStats> {
  return request<DocumentStats>({
    method: 'GET',
    url: '/documents/stats'
  })
}

export function getDocumentsApi(limit = 50, offset = 0, search?: string): Promise<DocumentListResponse> {
  return request<DocumentListResponse>({
    method: 'GET',
    url: '/documents',
    params: search ? { limit, offset, search } : { limit, offset }
  })
}

export function getAllDocumentIdsApi(search?: string): Promise<{ ids: string[]; total: number }> {
  return request<{ ids: string[]; total: number }>({
    method: 'GET',
    url: '/documents/ids',
    params: search ? { search } : undefined
  })
}

export function getDocumentApi(documentId: string): Promise<DocumentInfo> {
  return request<DocumentInfo>({
    method: 'GET',
    url: `/documents/${documentId}`
  })
}

export function deleteDocumentApi(documentId: string): Promise<void> {
  return request<void>({
    method: 'DELETE',
    url: `/documents/${documentId}`
  })
}

export function deleteDocumentsBatchApi(ids: string[]): Promise<{ deleted_count: number }> {
  return request<{ deleted_count: number }>({
    method: 'DELETE',
    url: '/documents/batch',
    data: { ids }
  })
}

export function getDocumentChunksApi(documentId: string): Promise<DocumentChunksResponse> {
  return request<DocumentChunksResponse>({
    method: 'GET',
    url: `/documents/${documentId}/chunks`
  })
}

export function searchDocumentsApi(query: string, topK = 5): Promise<SearchResponse> {
  return request<SearchResponse>({
    method: 'POST',
    url: '/documents/search',
    data: { query, top_k: topK }
  })
}

export function uploadDocumentApi(file: File): Promise<DocumentInfo> {
  const formData = new FormData()
  formData.append('file', file)

  const token = localStorage.getItem('access_token')
  const controller = new AbortController()
  const uploadTimeout = 180000

  const timeoutId = setTimeout(() => controller.abort(), uploadTimeout)

  return new Promise((resolve, reject) => {
    fetch('/api/documents/upload', {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: formData,
      signal: controller.signal
    }).then(async (response) => {
      clearTimeout(timeoutId)
      if (!response.ok) {
        let errorText = '上传失败'
        try {
          const errData = await response.json()
          const detail = errData.detail
          if (typeof detail === 'string') {
            errorText = detail
          } else if (Array.isArray(detail)) {
            errorText = detail.map((d: { msg?: string }) => d.msg || '').join('; ')
          } else if (detail) {
            errorText = JSON.stringify(detail)
          }
        } catch { /* ignore */ }
        reject(new Error(errorText))
        return
      }
      const data = await response.json()
      resolve(data)
    }).catch((err: Error) => {
      clearTimeout(timeoutId)
      if (err.name === 'AbortError') {
        reject(new Error('上传超时（3分钟），文档处理时间过长，请检查后端服务是否正常'))
      } else {
        reject(err)
      }
    })
  })
}
