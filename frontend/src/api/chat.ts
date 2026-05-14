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
  onAudio?: (audioBase64: string) => void
}

let abortController: AbortController | null = null
export const voiceAbortController: { current: AbortController | null } = { current: null }

export function stopStream() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

export function stopVoiceStream() {
  if (voiceAbortController.current) {
    voiceAbortController.current.abort()
    voiceAbortController.current = null
  }
}

export function isStreaming(): boolean {
  return abortController !== null && !abortController.signal.aborted
}

export function askStreamApi(message: string, sessionId: string | null, callbacks: StreamCallbacks, quickMode: boolean = false, voice: string = 'longanhuan', images: string[] = [], personalization: Record<string, number> = {}): AbortController {
  stopStream()

  const controller = new AbortController()
  abortController = controller
  const { onChunk, onDone, onError, onSessionId, onStatus, onToolCall, onToolResult, onAudio } = callbacks
  let aborted = false

  const token = localStorage.getItem('access_token')

  console.log('[快速模式] API层 quickMode =', quickMode, ', images =', images.length, ', personalization =', personalization, ', 请求体 =', { message: message.slice(0, 30), session_id: sessionId, quick_mode: quickMode, voice, personalization })

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ message, session_id: sessionId, quick_mode: quickMode, voice, images, personalization }),
    signal: controller.signal
  }).then(async (response) => {
    if (aborted) return
    if (!response.ok) {
      let errorText = '请求失败'
      try {
        const errData = await response.json()
        errorText = errData.detail || errorText
      } catch { /* ignore */ }
      if (!aborted) onError(errorText)
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      if (aborted) {
        reader.cancel().catch(() => {})
        return
      }
      const { done, value } = await reader.read()
      if (done) {
        if (!aborted) {
          onDone()
        }
        abortController = null
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (aborted) return
        if (!line.startsWith('data: ')) continue
        const dataStr = line.slice(6)

        if (dataStr === '[DONE]' || dataStr === '') {
          if (!aborted) onDone()
          abortController = null
          return
        }

        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.error) {
            if (!aborted) onError(parsed.error)
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
          if (parsed.a && onAudio) {
            onAudio(parsed.a)
          }
        } catch {
          // skip unparseable lines
        }
      }
    }
  }).catch((err) => {
    if (err.name === 'AbortError') {
      aborted = true
      onDone()
    } else if (!aborted) {
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
