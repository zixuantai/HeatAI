import { voiceAbortController, stopVoiceStream } from './chat'

export interface VoiceSendCallbacks {
  onTranscript: (text: string) => void
  onError: (error: string) => void
}

export interface TTSChunkCallbacks {
  onAudioChunk: (audioBase64: string) => void
  onDone: () => void
  onError: (error: string) => void
}

export function sendVoiceToBackend(audioBase64: string, callbacks: VoiceSendCallbacks): AbortController {
  stopVoiceStream()

  console.log('[Voice API] 发送语音到后端, base64长度:', audioBase64.length)

  const controller = new AbortController()
  voiceAbortController.current = controller
  const { onTranscript, onError } = callbacks
  let aborted = false

  const token = localStorage.getItem('access_token')

  fetch('/api/voice/asr', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ audio: audioBase64 }),
    signal: controller.signal
  }).then(async (response) => {
    if (aborted) return
    console.log('[Voice API] ASR响应状态:', response.status)
    if (!response.ok) {
      let errorText = '语音识别失败'
      try {
        const errData = await response.json()
        errorText = errData.detail || errorText
      } catch { /* ignore */ }
      console.error('[Voice API] ASR失败:', errorText)
      if (!aborted) onError(errorText)
      return
    }

    const data = await response.json()
    console.log('[Voice API] ASR返回数据:', data)
    const text = data?.data?.text
    if (!aborted && text !== null && text !== undefined) {
      if (text.trim()) {
        onTranscript(text.trim())
      } else {
        onError('未识别到语音内容')
      }
    } else {
      onError('语音识别返回数据异常')
    }
  }).catch((err) => {
    if (err.name === 'AbortError') {
      aborted = true
      console.log('[Voice API] 请求被中止')
    } else {
      console.error('[Voice API] 请求异常:', err)
      if (!aborted) onError(String(err))
    }
  })

  return controller
}

export function streamTTS(text: string, callbacks: TTSChunkCallbacks, quickMode: boolean = false): AbortController {
  stopVoiceStream()

  const controller = new AbortController()
  voiceAbortController.current = controller
  const { onAudioChunk, onDone, onError } = callbacks
  let aborted = false

  const token = localStorage.getItem('access_token')

  fetch('/api/voice/tts/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ text, quick_mode: quickMode }),
    signal: controller.signal
  }).then(async (response) => {
    if (aborted) return
    if (!response.ok) {
      let errorText = '语音合成失败'
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
        if (!aborted) onDone()
        voiceAbortController.current = null
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
          voiceAbortController.current = null
          return
        }

        try {
          const parsed = JSON.parse(dataStr)
          if (parsed.error) {
            if (!aborted) onError(parsed.error)
            return
          }
          if (parsed.audio) {
            onAudioChunk(parsed.audio)
          }
        } catch {
          // skip
        }
      }
    }
  }).catch((err) => {
    if (err.name === 'AbortError') {
      aborted = true
    } else if (!aborted) {
      onError(String(err))
    }
    voiceAbortController.current = null
  })

  return controller
}