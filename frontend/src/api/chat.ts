import { request } from '@/utils/request'
import type { ChatResponseData, SessionInfo, SessionDetail, ToolCallInfo, ToolResultInfo } from '@/types'

export function askApi(message: string, sessionId?: string): Promise<ChatResponseData> {
  return request<ChatResponseData>({
    method: 'POST',
    url: '/chat/ask',
    data: { message, session_id: sessionId || null },
    timeout: 120000
  })
}

export interface StreamCallbacks {
  onChunk: (text: string) => void
  onDone: () => void
  onError: (error: string) => void
  onSessionId?: (sessionId: string) => void
  onStatus?: (status: string) => void
  onToolCall?: (info: ToolCallInfo) => void
  onToolResult?: (info: ToolResultInfo) => void
}

let abortController: AbortController | null = null

export function stopStream() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

export function askStreamApi(message: string, sessionId: string | null, callbacks: StreamCallbacks, quickMode: boolean = false): AbortController {
  stopStream()

  const controller = new AbortController()
  abortController = controller
  const { onChunk, onDone, onError, onSessionId, onStatus, onToolCall, onToolResult } = callbacks

  const token = localStorage.getItem('access_token')

  console.log('[快速模式] API层 quickMode =', quickMode, ', 请求体 =', { message: message.slice(0, 30), session_id: sessionId, quick_mode: quickMode })

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ message, session_id: sessionId, quick_mode: quickMode }),
    signal: controller.signal
  }).then(async (response) => {
    if (!response.ok) {
      let errorText = '请求失败'
      try {
        const errData = await response.json()
        errorText = errData.detail || errorText
      } catch { /* ignore */ }
      onError(errorText)
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        onDone()
        abortController = null
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const dataStr = line.slice(6)

        if (dataStr === '[DONE]' || dataStr === '') {
          onDone()
          abortController = null
          return
        }

        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.error) {
            onError(parsed.error)
            return
          }
          if (parsed.session_id && onSessionId) {
            onSessionId(parsed.session_id)
          }
          if (parsed.s && onStatus) {
            onStatus(parsed.s)
          }
          if (parsed.tc && onToolCall) {
            onToolCall(parsed.tc)
          }
          if (parsed.tr && onToolResult) {
            onToolResult(parsed.tr)
          }
          if (parsed.c != null) {
            onChunk(parsed.c)
          }
        } catch {
          // skip unparseable lines
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError(String(err))
    }
    abortController = null
  })

  return controller
}

export function getSessionsApi(limit = 50, offset = 0): Promise<SessionInfo[]> {
  return request<SessionInfo[]>({
    method: 'GET',
    url: '/chat/sessions',
    params: { limit, offset }
  })
}

export function getSessionDetailApi(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>({
    method: 'GET',
    url: `/chat/sessions/${sessionId}`
  })
}

export function deleteSessionApi(sessionId: string): Promise<void> {
  return request<void>({
    method: 'DELETE',
    url: `/chat/sessions/${sessionId}`
  })
}

export function updateSessionTitleApi(sessionId: string, title: string): Promise<SessionInfo> {
  return request<SessionInfo>({
    method: 'PATCH',
    url: `/chat/sessions/${sessionId}`,
    data: { title }
  })
}

export function togglePinSessionApi(sessionId: string, isPinned: boolean): Promise<SessionInfo> {
  return request<SessionInfo>({
    method: 'PATCH',
    url: `/chat/sessions/${sessionId}/pin`,
    data: { is_pinned: isPinned }
  })
}
