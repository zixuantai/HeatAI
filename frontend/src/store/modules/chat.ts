import { defineStore } from 'pinia'
import { reactive } from 'vue'
import type { ChatMessage } from '@/types'
import { askStreamApi, stopStream as stopStreamApi } from '@/api/chat'
import type { StreamCallbacks } from '@/api/chat'

const NEW_SESSION_KEY = '__new__'

export interface SessionChatState {
  messages: ChatMessage[]
  loading: boolean
  streamingContent: string
  streamMsgId: string
  pendingStreamContent: string
  statusMessage: string
  abortController: AbortController | null
  initialized: boolean
  hasAudio: boolean
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
      statusMessage: '',
      abortController: null,
      initialized: false,
      hasAudio: false
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
    state.messages = messages
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
    onSessionCreated?: (sessionId: string) => void,
    onStreamError?: (error: string) => void
  ) {
    const state = getOrCreate(storeKey)

    if (state.abortController) {
      state.abortController.abort()
    }

    state.loading = true
    state.streamingContent = ''
    state.pendingStreamContent = ''
    state.statusMessage = ''
    state.initialized = true
    state.hasAudio = true

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
          s.messages.push({
            id: streamMsgId,
            role: 'assistant',
            content: '',
            timestamp: Date.now()
          })
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
      onDone() {
        if (!sessions[currentKey]) return
        finishStreamForSession(currentKey)
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

    const controller = askStreamApi(content, apiSessionId, callbacks, quickMode, 'longanhuan', images)
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