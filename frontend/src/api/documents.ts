import { request } from '@/utils/request'
import type { DocumentInfo, DocumentListResponse, DocumentChunksResponse, SearchResponse } from '@/types'

export function getDocumentsApi(limit = 50, offset = 0): Promise<DocumentListResponse> {
  return request<DocumentListResponse>({
    method: 'GET',
    url: '/documents',
    params: { limit, offset }
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

  return new Promise((resolve, reject) => {
    fetch('/api/documents/upload', {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: formData
    }).then(async (response) => {
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
    }).catch(reject)
  })
}
