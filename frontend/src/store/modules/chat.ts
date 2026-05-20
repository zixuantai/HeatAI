import { defineStore } from 'pinia'
import { reactive } from 'vue'
import type { ChatMessage, SourceRef } from '@/types'
import { askStreamApi, stopStream as stopStreamApi } from '@/api/chat'
import type { StreamCallbacks } from '@/api/chat'
import { useAuthStore } from '@/store/modules/auth'

const NEW_SESSION_KEY = '__new__'

export interface SessionChatState {
  messages: ChatMessage[]
  loading: boolean
  streamingContent: string
  streamMsgId: string
  pendingStreamContent: string
  pendingSources: SourceRef[]
  statusMessage: string
  abortController: AbortController | null
  initialized: boolean
  hasAudio: boolean
  audioChunks: string[]
}

export const useChatStore = defineStore('chat', () => {
  const sessions = reactive<Record<string, SessionChatState>>({})

  function createState(): SessionChatState {
    return {
      messages: [],
      loading: false,
      streamingContent: '',
      streamMsgId: '',
      pendingStreamContent: '',
      pendingSources: [],
      statusMessage: '',
      abortController: null,
      initialized: false,
      hasAudio: false,
      audioChunks: []
    }
  }

  function getOrCreate(sessionId: string): SessionChatState {
    if (!sessions[sessionId]) {
      sessions[sessionId] = createState()
    }
    return sessions[sessionId]
  }

  function initSession(sessionId: string, messages: ChatMessage[]) {
    const state = getOrCreate(sessionId)
    // 防止用后端数据覆盖流式输出期间已存在消息
    if (state.messages.length === 0) {
      state.messages = messages
    }
    state.initialized = true
  }

  function clearSession(sessionId: string) {
    const state = sessions[sessionId]
    if (state && state.abortController) {
      state.abortController.abort()
    }
    delete sessions[sessionId]
  }

  function clearAllSessions() {
    for (const id of Object.keys(sessions)) {
      clearSession(id)
    }
  }

  function startStream(
    storeKey: string,
    apiSessionId: string | null,
    content: string,
    images: string[],
    quickMode: boolean,
    onAudioChunk?: (text: string) => void,
    onServerAudio?: (audioBase64: string) => void,
    onSessionCreated?: (sessionId: string) => void,
    onStreamError?: (error: string) => void,
    onStreamDone?: () => void
  ) {
    const state = getOrCreate(storeKey)

    if (state.abortController) {
      state.abortController.abort()
    }

    state.loading = true
    state.streamingContent = ''
    state.pendingStreamContent = ''
    state.pendingSources = []
    state.statusMessage = ''
    state.initialized = true
    state.hasAudio = !!onAudioChunk

    let msgIdCounter = state.messages.length
    const streamMsgId = `msg_${Date.now()}_${++msgIdCounter}`
    state.streamMsgId = streamMsgId

    let placeholderPushed = false

    let currentKey = storeKey

    const callbacks: StreamCallbacks = {
      onChunk(text: string) {
        const s = sessions[currentKey]
        if (!s) return

        s.streamingContent += text
        if (onAudioChunk) {
          onAudioChunk(text)
        }
        if (!placeholderPushed) {
          placeholderPushed = true
          const hasSources = s.pendingSources.length > 0
          console.log('[ChatStore] onChunk - 推送assistant占位消息, pendingSources:', hasSources ? '有' + s.pendingSources.length + '个来源' : '空')
          s.messages.push({
            id: streamMsgId,
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            sources: hasSources ? s.pendingSources : undefined
          })
          s.pendingSources = []
        }
        s.pendingStreamContent = s.streamingContent
        const msg = s.messages.find(m => m.id === streamMsgId)
        if (msg) {
          msg.content = s.streamingContent
        }
      },
      onSessionId(newSessionId: string) {
        if (currentKey === NEW_SESSION_KEY) {
          const oldState = sessions[NEW_SESSION_KEY]
          if (oldState) {
            oldState.abortController = null
            oldState.initialized = true
            sessions[newSessionId] = oldState
            delete sessions[NEW_SESSION_KEY]
            currentKey = newSessionId
          }
        }
        if (onSessionCreated) {
          onSessionCreated(newSessionId)
        }
      },
      onStatus(status: string) {
        const s = sessions[currentKey]
        if (!s) return
        const statusTextMap: Record<string, string> = {
          analyzing: '正在分析您的问题...',
          retrieving: '正在检索相关知识...',
          generating: '正在生成回答...',
        }
        s.statusMessage = statusTextMap[status] || status
      },
      onAudio(audioBase64: string) {
        console.log('[ChatStore] onAudio 收到音频, 长度:', audioBase64.length)
        const s = sessions[currentKey]
        if (s) {
          s.audioChunks.push(audioBase64)
          s.hasAudio = true
        }
        if (onServerAudio) {
          onServerAudio(audioBase64)
        } else {
          console.log('[ChatStore] onAudio - onServerAudio 未设置, 音频丢弃')
        }
      },
      onSources(sources: SourceRef[]) {
        console.log('[ChatStore] onSources 收到来源, 数量:', sources.length, '数据:', JSON.stringify(sources))
        const s = sessions[currentKey]
        if (!s) {
          console.log('[ChatStore] onSources - session未找到, currentKey:', currentKey)
          return
        }
        if (placeholderPushed) {
          const msg = s.messages.find(m => m.id === streamMsgId)
          if (msg) {
            console.log('[ChatStore] onSources - 已推placeholder, 直接设置sources到消息')
            msg.sources = sources
          }
        } else {
          console.log('[ChatStore] onSources - 未推placeholder, 存入pendingSources')
          s.pendingSources = sources
        }
      },
      onDone() {
        if (!sessions[currentKey]) return
        finishStreamForSession(currentKey)
        if (onStreamDone) onStreamDone()
      },
      onError(error: string) {
        const s = sessions[currentKey]
        if (!s) return
        if (!placeholderPushed) {
          s.loading = false
          if (onStreamError) onStreamError(error)
          return
        }
        const msg = s.messages.find(m => m.id === streamMsgId)
        if (msg) {
          msg.content = s.streamingContent
        }
        s.streamingContent = ''
        s.streamMsgId = ''
        s.loading = false
        if (onStreamError) onStreamError(error)
      }
    }

    const authStore = useAuthStore()
    const voiceType = localStorage.getItem(`heatai_voice_type_${authStore.user?.id || ''}`) || 'longanhuan'
    console.log('[ChatStore] startStream - voiceType从localStorage读取:', voiceType, 'key:', `heatai_voice_type_${authStore.user?.id || ''}`)
    const userId = authStore.user?.id || ''
    const personalizationKeys = ['gentle', 'enthusiastic', 'structure', 'emoji']
    const personalization: Record<string, number> = {}
    for (const k of personalizationKeys) {
      const stored = localStorage.getItem(`heatai_personalization_${userId}_${k}`)
      personalization[k] = stored !== null ? Number(stored) : 0
    }
    const controller = askStreamApi(content, apiSessionId, callbacks, quickMode, voiceType, images, personalization)
    state.abortController = controller
  }

  function finishStreamForSession(sessionId: string) {
    const state = sessions[sessionId]
    if (!state) return

    if (state.pendingStreamContent) {
      const msg = state.messages.find(m => m.id === state.streamMsgId)
      if (msg) {
        msg.content = state.pendingStreamContent
      }
      state.pendingStreamContent = ''
    }
    if (state.streamingContent) {
      const msg = state.messages.find(m => m.id === state.streamMsgId)
      if (msg) {
        msg.content = state.streamingContent
      }
    }
    state.streamingContent = ''
    state.streamMsgId = ''
    state.statusMessage = ''
    state.loading = false
    state.abortController = null
  }

  function stopStreamForSession(sessionId: string) {
    const state = sessions[sessionId]
    if (!state) return

    stopStreamApi()

    if (state.pendingStreamContent) {
      const msg = state.messages.find(m => m.id === state.streamMsgId)
      if (msg) {
        msg.content = state.pendingStreamContent
      }
      state.pendingStreamContent = ''
    }
    if (state.streamingContent) {
      const msg = state.messages.find(m => m.id === state.streamMsgId)
      if (msg) {
        msg.content = state.streamingContent
      }
    }
    state.streamingContent = ''
    state.streamMsgId = ''
    state.statusMessage = ''
    state.loading = false
    state.abortController = null
  }

  return {
    sessions,
    getOrCreate,
    initSession,
    clearSession,
    clearAllSessions,
    startStream,
    stopStreamForSession,
    finishStreamForSession
  }
})