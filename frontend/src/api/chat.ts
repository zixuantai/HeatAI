import { request } from '@/utils/request'
import type { ChatResponseData } from '@/types'

export function askApi(message: string): Promise<ChatResponseData> {
  return request<ChatResponseData>({
    method: 'POST',
    url: '/chat/ask',
    data: { message },
    timeout: 120000
  })
}

export interface StreamCallbacks {
  onChunk: (text: string) => void
  onDone: () => void
  onError: (error: string) => void
}

let abortController: AbortController | null = null

export function stopStream() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

export function askStreamApi(message: string, callbacks: StreamCallbacks): AbortController {
  stopStream()

  const controller = new AbortController()
  abortController = controller
  const { onChunk, onDone, onError } = callbacks

  const token = localStorage.getItem('access_token')

  fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ message }),
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
