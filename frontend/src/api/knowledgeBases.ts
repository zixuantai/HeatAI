import { request } from '@/utils/request'
import type { KnowledgeBase, KnowledgeBaseListResponse, CreateKnowledgeBaseRequest, UpdateKnowledgeBaseRequest, SessionDetail } from '@/types'

export function createKnowledgeBaseApi(data: CreateKnowledgeBaseRequest): Promise<KnowledgeBase> {
  return request<KnowledgeBase>({
    method: 'POST',
    url: '/knowledge-bases',
    data
  })
}

export function getKnowledgeBasesApi(params: {
  search?: string
  sort_by?: string
  limit?: number
  offset?: number
}): Promise<KnowledgeBaseListResponse> {
  return request<KnowledgeBaseListResponse>({
    method: 'GET',
    url: '/knowledge-bases',
    params
  })
}

export function getKnowledgeBaseApi(kbId: string): Promise<KnowledgeBase> {
  return request<KnowledgeBase>({
    method: 'GET',
    url: `/knowledge-bases/${kbId}`
  })
}

export function updateKnowledgeBaseApi(kbId: string, data: UpdateKnowledgeBaseRequest): Promise<KnowledgeBase> {
  return request<KnowledgeBase>({
    method: 'PUT',
    url: `/knowledge-bases/${kbId}`,
    data
  })
}

export function deleteKnowledgeBaseApi(kbId: string): Promise<void> {
  return request<void>({
    method: 'DELETE',
    url: `/knowledge-bases/${kbId}`
  })
}

export function toggleLikeApi(kbId: string): Promise<{ is_liked: boolean }> {
  return request<{ is_liked: boolean }>({
    method: 'POST',
    url: `/knowledge-bases/${kbId}/like`
  })
}

export function toggleFavoriteApi(kbId: string): Promise<{ is_favorited: boolean }> {
  return request<{ is_favorited: boolean }>({
    method: 'POST',
    url: `/knowledge-bases/${kbId}/favorite`
  })
}

export function updateQuickQuestionsApi(kbId: string, quickQuestions: string[]): Promise<{ quick_questions: string[] }> {
  return request<{ quick_questions: string[] }>({
    method: 'PUT',
    url: `/knowledge-bases/${kbId}/quick-questions`,
    data: { quick_questions: quickQuestions }
  })
}

export function generateQuickQuestionsApi(kbId: string): Promise<{ quick_questions: string[] }> {
  return request<{ quick_questions: string[] }>({
    method: 'POST',
    url: `/knowledge-bases/${kbId}/quick-questions/generate`
  })
}

export function previewQuickQuestionsApi(name: string, description: string): Promise<any> {
  return request({
    method: 'POST',
    url: '/knowledge-bases/quick-questions/preview',
    data: { name, description }
  })
}

export function toggleJoinApi(kbId: string): Promise<any> {
  return request({
    method: 'POST',
    url: `/knowledge-bases/${kbId}/join`
  })
}

export function uploadDocumentToKbApi(kbId: string, file: File): Promise<{ document_id: string; filename: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return request<{ document_id: string; filename: string; status: string }>({
    method: 'POST',
    url: `/knowledge-bases/${kbId}/documents/upload`,
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function getKbDocumentsApi(kbId: string, limit = 50, offset = 0): Promise<{ total: number; items: any[] }> {
  return request<{ total: number; items: any[] }>({
    method: 'GET',
    url: `/knowledge-bases/${kbId}/documents`,
    params: { limit, offset }
  })
}

export function removeDocumentFromKbApi(kbId: string, documentId: string): Promise<void> {
  return request<void>({
    method: 'DELETE',
    url: `/knowledge-bases/${kbId}/documents/${documentId}`
  })
}
