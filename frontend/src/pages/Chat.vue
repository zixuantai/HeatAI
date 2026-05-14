<template>
  <div class="chat-container" :class="{ 'has-messages': messages.length > 0 }">
    <div class="chat-topbar">
      <div class="topbar-brand">
        <span class="topbar-text">HeatAI</span>
      </div>
    </div>

    <div class="chat-body" :class="{ 'is-empty': messages.length === 0 }">
      <div v-if="messages.length === 0" class="chat-welcome">
        <h2>欢迎使用 HeatAI 供热智能客服</h2>
        <p>我是您的供热服务助手，可以帮您解答供暖相关问题</p>
      </div>

      <div v-else class="chat-messages" ref="messagesContainer">
        <div class="messages-inner">
          <div
            v-for="(msg, index) in messages"
            :key="msg.id"
            class="message-row"
            :class="msg.role"
            :style="{ animationDelay: `${index * 0.05}s` }"
          >
            <div class="message-bubble" :class="msg.role">
              <div
                v-if="msg.role === 'assistant'"
                class="message-text markdown-body"
                v-html="renderMarkdownCached(msg.content)"
              ></div>
              <div v-else class="message-text">{{ msg.content }}</div>
              <div v-if="msg.images && msg.images.length > 0" class="message-image-list">
                <img
                  v-for="(img, i) in msg.images"
                  :key="i"
                  :src="img"
                  alt="用户上传图片"
                  class="message-image-thumb"
                />
              </div>
            </div>
          </div>

          <div v-if="loading && streamingContent === ''" class="message-row assistant thinking-row">
            <div class="message-bubble assistant thinking">
              <span class="thinking-text">{{ statusMessage || '正在思考' }}</span>
              <span class="typing-dots">
                <span class="typing-dot" :style="{ animationDelay: '0s' }"></span>
                <span class="typing-dot" :style="{ animationDelay: '0.2s' }"></span>
                <span class="typing-dot" :style="{ animationDelay: '0.4s' }"></span>
              </span>
            </div>
          </div>

          <div v-if="hasAudio" class="audio-control-bar">
            <button
              class="audio-toggle-btn"
              :class="{ muted: !isAudioPlaying || isAudioMuted }"
              @click="togglePlay"
            >
              <div v-if="isAudioPlaying && !isAudioMuted" class="audio-wave-icon">
                <span v-for="i in 4" :key="i" class="audio-wave-bar" :style="{ animationDelay: `${i * 0.15}s` }"></span>
              </div>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                <line x1="23" y1="9" x2="17" y2="15" />
                <line x1="17" y1="9" x2="23" y2="15" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <div class="input-wrapper" :class="{ 'voice-active': isVoiceMode, 'is-expanded': isMultiLine }">
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            multiple
            hidden
            @change="handleImageSelect"
          />
          <button
            class="image-upload-btn"
            :class="{ 'has-images': uploadedImages.length > 0 }"
            @click="triggerImageUpload"
            title="上传图片"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
          <el-tooltip
            effect="dark"
            content="快速模式回答质量会低一些哦"
            placement="top"
            :show-after="300"
            :disabled="quickMode"
            popper-class="quick-tooltip"
          >
            <button
              class="quick-mode-toggle"
              :class="{ active: quickMode }"
              @click="toggleQuickMode"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              <span>快速模式</span>
            </button>
          </el-tooltip>
          <div class="input-content-area" @paste="handlePaste">
            <div v-if="uploadedImages.length > 0" class="inline-image-bar">
              <div v-for="(img, idx) in uploadedImages" :key="idx" class="inline-image-item">
                <img :src="img" alt="预览图片" class="inline-image-thumb" />
                <button class="inline-image-remove" @click="removeImage(idx)" title="移除图片">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            </div>
            <el-input
              ref="inputRef"
              v-model="inputMessage"
              type="textarea"
              :rows="1"
              :autosize="{ minRows: 1, maxRows: 6 }"
              :placeholder="isVoiceMode ? '' : '有问题，尽管问'"
              resize="none"
              class="chat-input"
              :disabled="isVoiceMode"
              @keydown.enter.exact.prevent="handleSend"
            />
          </div>
          <VoiceInput
            ref="voiceInputRef"
            @send="handleVoiceSend"
            @stop="handleVoiceStop"
            @update:voiceMode="onVoiceModeChange"
            @update:isSpeaking="onSpeakingChange"
          />
          <div v-if="isVoiceMode && !isSpeaking" class="voice-hint-overlay">请讲话</div>
          <div v-if="isSpeaking" class="voice-wave-overlay">
            <div
              v-for="i in 32" :key="i"
              class="voice-wave-bar"
              :style="{ animationDelay: `${i * 0.1}s` }"
            ></div>
          </div>
          <button
            v-if="!loading"
            class="send-btn"
            :disabled="!inputMessage.trim() && uploadedImages.length === 0"
            title="发送消息"
            @click="handleSend"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="19" x2="12" y2="5"></line>
              <polyline points="5 12 12 5 19 12"></polyline>
            </svg>
          </button>
          <button
            v-else
            class="stop-btn"
            title="停止生成"
            @click="handleTotalStop"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <rect x="4" y="4" width="16" height="16" rx="3" />
            </svg>
          </button>
        </div>
        <div v-if="messages.length === 0" class="quick-questions">
          <el-tag
            v-for="q in quickQuestions"
            :key="q"
            class="quick-tag"
            @click="handleQuickQuestion(q)"
          >
            {{ q }}
          </el-tag>
        </div>
        <p v-if="messages.length > 0" class="input-hint">内容由AI生成，仅供参考</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ElInput } from 'element-plus'
import { stopVoiceStream, getSessionDetailApi } from '@/api/chat'
import { sendVoiceToBackend } from '@/api/voice'
import type { ChatMessage } from '@/types'
import { marked } from 'marked'
import hljs from 'highlight.js'
import { useAuthStore } from '@/store/modules/auth'
import { useChatStore } from '@/store/modules/chat'
import VoiceInput from '@/components/chat/VoiceInput.vue'
import { useAudioPlayer } from '@/composables/useAudioPlayer'

const props = defineProps<{
  sessionId?: string
}>()

const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()

marked.setOptions({
  breaks: true,
  gfm: true
})

const langLabel: Record<string, string> = {
  plaintext: '文本', python: 'Python', py: 'Python',
  cpp: 'C++', cc: 'C++', cxx: 'C++', c: 'C',
  javascript: 'JavaScript', js: 'JavaScript', typescript: 'TypeScript', ts: 'TypeScript',
  java: 'Java', go: 'Go', rust: 'Rust', rs: 'Rust',
  html: 'HTML', css: 'CSS', sql: 'SQL',
  bash: 'Bash', shell: 'Shell', sh: 'Shell', zsh: 'Shell',
  json: 'JSON', xml: 'XML', yaml: 'YAML', yml: 'YAML',
  markdown: 'Markdown', md: 'Markdown', php: 'PHP',
  ruby: 'Ruby', rb: 'Ruby', swift: 'Swift', kotlin: 'Kotlin',
}

function getLangLabel(lang: string): string {
  return langLabel[lang] || lang
}

const renderer = new marked.Renderer()
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  const validLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  const highlighted = hljs.highlight(text, { language: validLang }).value
  const displayName = getLangLabel(validLang)
  return `
    <div class="code-block-wrapper">
      <div class="code-block-header">
        <span class="code-lang-label">${displayName}</span>
        <button class="code-copy-btn" onclick="(function(btn){var p=btn.parentElement.nextElementSibling;var t=p.innerText;navigator.clipboard.writeText(t).then(function(){btn.textContent='已复制';setTimeout(function(){btn.textContent='复制'},2000)})})(this)">复制</button>
      </div>
      <pre><code class="hljs language-${validLang}">${highlighted}</code></pre>
    </div>`
}
renderer.codespan = function ({ text }: { text: string }) {
  return `<code class="inline-code">${text}</code>`
}
marked.setOptions({ renderer })

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

const inputMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const inputRef = ref<InstanceType<typeof ElInput>>()
const fileInputRef = ref<HTMLInputElement>()
const quickMode = ref(false)
const isVoiceMode = ref(false)
const isSpeaking = ref(false)
const voiceInputRef = ref<InstanceType<typeof VoiceInput>>()
const uploadedImages = ref<string[]>([])
const isMultiLine = ref(false)
const streamCreatedSessionId = ref<string | null>(null)

const NEW_SESSION_KEY = '__new__'

const sessionKey = computed(() => props.sessionId || NEW_SESSION_KEY)

const messages = computed(() => {
  const s = chatStore.sessions[sessionKey.value]
  return s ? s.messages : []
})
const loading = ref(false)
const streamingContent = ref('')
const statusMessage = ref('')

watch(() => {
  const s = chatStore.sessions[sessionKey.value]
  if (!s) return { loading: false, streamingContent: '', statusMessage: '' }
  return { loading: s.loading, streamingContent: s.streamingContent, statusMessage: s.statusMessage }
}, (data) => {
  loading.value = data.loading
  streamingContent.value = data.streamingContent
  statusMessage.value = data.statusMessage
}, { immediate: true, deep: true })

const { hasAudio, isAudioPlaying, isAudioMuted, initAudioStream, handleAudioChunk, togglePlay, finishAudio, stopPlayback, cleanup } = useAudioPlayer()

watch(() => {
  const s = chatStore.sessions[sessionKey.value]
  return s ? s.hasAudio : false
}, (val) => {
  hasAudio.value = val
}, { immediate: true })

function toggleQuickMode() {
  quickMode.value = !quickMode.value
  console.log('[快速模式] 切换为:', quickMode.value)
}

function triggerImageUpload() {
  fileInputRef.value?.click()
}

function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  const maxCount = 5
  const remaining = maxCount - uploadedImages.value.length
  if (remaining <= 0) {
    ElMessage.warning(`最多只能上传 ${maxCount} 张图片`)
    input.value = ''
    return
  }

  const filesToProcess = Math.min(files.length, remaining)
  let loaded = 0
  let skipped = 0

  const onAllDone = () => {
    input.value = ''
    focusInput()
  }

  for (let i = 0; i < filesToProcess; i++) {
    const file = files[i]
    if (!file.type.startsWith('image/')) {
      skipped++
      if (loaded + skipped === filesToProcess) onAllDone()
      continue
    }

    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning(`图片 "${file.name}" 超过 10MB，已跳过`)
      skipped++
      if (loaded + skipped === filesToProcess) onAllDone()
      continue
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = e.target?.result as string
      if (base64) {
        uploadedImages.value.push(base64)
      }
      loaded++
      if (loaded + skipped === filesToProcess) {
        onAllDone()
      }
    }
    reader.readAsDataURL(file)
  }

  if (files.length > filesToProcess) {
    ElMessage.warning(`最多上传 ${maxCount} 张，已自动选取前 ${filesToProcess} 张`)
  }
}

function removeImage(index: number) {
  uploadedImages.value.splice(index, 1)
  focusInput()
}

function handlePaste(event: ClipboardEvent) {
  const items = event.clipboardData?.items
  if (!items) return

  const maxCount = 5
  const remaining = maxCount - uploadedImages.value.length
  if (remaining <= 0) {
    ElMessage.warning(`最多只能上传 ${maxCount} 张图片`)
    return
  }

  const imageItems: DataTransferItem[] = []
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.startsWith('image/')) {
      imageItems.push(item)
    }
  }

  if (imageItems.length === 0) return

  event.preventDefault()

  const toProcess = Math.min(imageItems.length, remaining)
  let loaded = 0
  let skipped = 0

  const onAllDone = () => {
    focusInput()
  }

  for (let i = 0; i < toProcess; i++) {
    const file = imageItems[i].getAsFile()
    if (!file) {
      skipped++
      if (loaded + skipped === toProcess) onAllDone()
      continue
    }

    if (file.size > 10 * 1024 * 1024) {
      ElMessage.warning('图片超过 10MB，已跳过')
      skipped++
      if (loaded + skipped === toProcess) onAllDone()
      continue
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = e.target?.result as string
      if (base64) {
        uploadedImages.value.push(base64)
      }
      loaded++
      if (loaded + skipped === toProcess) {
        onAllDone()
      }
    }
    reader.readAsDataURL(file)
  }

  if (imageItems.length > toProcess) {
    ElMessage.warning(`最多上传 ${maxCount} 张，已自动选取前 ${toProcess} 张`)
  }
}

const markdownCache = new Map<string, string>()
function renderMarkdownCached(text: string): string {
  const cached = markdownCache.get(text)
  if (cached !== undefined) return cached
  const html = marked.parse(text) as string
  markdownCache.set(text, html)
  return html
}

const quickQuestions = [
  '暖气不热怎么办？',
  '供暖温度标准是多少？',
  '如何缴纳供暖费？',
  '报修流程是怎样的？'
]

let msgIdCounter = 0
function genId() {
  return `msg_${Date.now()}_${++msgIdCounter}`
}

function focusInput() {
  nextTick(() => {
    inputRef.value?.focus()
  })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function loadSessionMessages(sessionId: string) {
  const existing = chatStore.sessions[sessionId]
  if (existing && (existing.messages.length > 0 || existing.loading)) {
    nextTick(() => scrollToBottom())
    return
  }

  try {
    const detail = await getSessionDetailApi(sessionId)
    if (detail && detail.messages) {
      const msgs: ChatMessage[] = detail.messages.map(m => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: new Date(m.created_at).getTime()
      }))
      const cur = chatStore.sessions[sessionId]
      if (cur && cur.loading) {
        return
      }
      chatStore.initSession(sessionId, msgs)
      nextTick(() => scrollToBottom())
    }
  } catch {
    ElMessage.error('加载对话记录失败')
  }
}

function handleQuickQuestion(question: string) {
  if (!authStore.isAuthenticated) {
    sessionStorage.setItem('pending_question', question)
    router.push({ name: 'Login', query: { redirect: '/chat' } })
    return
  }
  inputMessage.value = question
  handleSend()
}

let pendingScrollRafId: number | null = null
function scheduleScrollToBottom() {
  if (pendingScrollRafId !== null) return
  pendingScrollRafId = requestAnimationFrame(() => {
    pendingScrollRafId = null
    scrollToBottom()
  })
}

onMounted(() => {
  const pendingQuestion = sessionStorage.getItem('pending_question')
  if (pendingQuestion) {
    inputMessage.value = pendingQuestion
    sessionStorage.removeItem('pending_question')
  }
  if (props.sessionId) {
    const existing = chatStore.sessions[props.sessionId]
    if (existing && (existing.messages.length > 0 || existing.loading)) {
      nextTick(() => scrollToBottom())
    } else {
      loadSessionMessages(props.sessionId)
    }
  } else {
    inputMessage.value = ''
    focusInput()
  }
})

onBeforeUnmount(() => {
  if (pendingScrollRafId !== null) {
    cancelAnimationFrame(pendingScrollRafId)
    pendingScrollRafId = null
  }
  cleanup()
})

watch(() => props.sessionId, (newId, oldId) => {
  if (streamCreatedSessionId.value && newId === streamCreatedSessionId.value) {
    streamCreatedSessionId.value = null
    return
  }

  stopPlayback()

  inputMessage.value = ''

  if (newId) {
    const existing = chatStore.sessions[newId]
    if (existing && (existing.messages.length > 0 || existing.loading)) {
      nextTick(() => scrollToBottom())
      return
    }

    loadSessionMessages(newId)
  } else {
    if (voiceInputRef.value) {
      voiceInputRef.value.disableVoiceMode()
    }
    focusInput()
  }
})

watch(streamingContent, (newVal) => {
  if (newVal) {
    scheduleScrollToBottom()
  }
})

watch(inputMessage, () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      const textarea = inputRef.value?.$el?.querySelector('textarea') as HTMLTextAreaElement | null
      if (textarea) {
        const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight) || 24
        isMultiLine.value = textarea.scrollHeight > lineHeight * 1.8
      }
    })
  })
})

function doStop(sessionId: string) {
  chatStore.stopStreamForSession(sessionId)
  cleanup()
  finishAudio()
  if (isVoiceMode.value && voiceInputRef.value) {
    voiceInputRef.value.resumeVAD()
  }
}

function handleStop() {
  doStop(sessionKey.value)
}

function handleTotalStop() {
  stopVoiceStream()
  cleanup()
  if (voiceInputRef.value) {
    voiceInputRef.value.handleStop()
  }
  doStop(sessionKey.value)
}

function handleVoiceStop() {
  stopVoiceStream()
  cleanup()
  doStop(sessionKey.value)
}

function onVoiceModeChange(value: boolean) {
  isVoiceMode.value = value
  if (!value) {
    focusInput()
  }
}

function onSpeakingChange(value: boolean) {
  isSpeaking.value = value
}

function handleVoiceSend(audioBase64: string) {
  console.log('[Chat] 收到语音数据, base64长度:', audioBase64.length)

  if (!authStore.isAuthenticated) {
    router.push({ name: 'Login', query: { redirect: '/chat' } })
    return
  }

  if (loading.value) {
    handleStop()
  }

  sendVoiceToBackend(audioBase64, {
    onTranscript(text: string) {
      console.log('[Chat] ASR识别结果:', text)
      if (text.trim()) {
        inputMessage.value = text.trim()
        handleSend()
      }
    },
    onError(error: string) {
      console.error('[Chat] ASR错误:', error)
      ElMessage.error(error)
    }
  })
}

async function handleSend() {
  const content = inputMessage.value.trim()
  const hasImages = uploadedImages.value.length > 0
  if (!content && !hasImages) return

  if (!authStore.isAuthenticated) {
    sessionStorage.setItem('pending_question', content)
    router.push({ name: 'Login', query: { redirect: '/chat' } })
    return
  }

  if (loading.value) {
    handleStop()
  }

  cleanup()

  const currentImages = [...uploadedImages.value]
  uploadedImages.value = []

  const sid = sessionKey.value
  const state = chatStore.getOrCreate(sid)

  const userMsg: ChatMessage = {
    id: genId(),
    role: 'user',
    content: content || '',
    timestamp: Date.now(),
    images: currentImages.length > 0 ? currentImages : undefined
  }

  state.messages.push(userMsg)

  inputMessage.value = ''
  focusInput()
  scrollToBottom()

  const enableVoice = localStorage.getItem(`heatai_voice_enabled_${authStore.user?.id || ''}`) !== 'false'
  if (enableVoice) {
    initAudioStream()
  }

  if (isVoiceMode.value && voiceInputRef.value) {
    voiceInputRef.value.pauseVAD()
  }

  chatStore.startStream(
    sid,
    props.sessionId || null,
    content || '',
    currentImages,
    quickMode.value,
    enableVoice ? (text: string) => {
      handleAudioChunk(text)
    } : undefined,
    (newSessionId: string) => {
      if (!props.sessionId) {
        streamCreatedSessionId.value = newSessionId
        router.replace(`/chat/${newSessionId}`)
      }
    },
    (error: string) => {
      ElMessage.error(error || '请求失败，请稍后重试')
    }
  )
}
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  font-family: var(--font-family);
  -webkit-font-smoothing: antialiased;
  position: relative;
  overflow: hidden;
}

/* ── Atmospheric Background Blobs ────────────────────── */
.chat-container::before {
  content: '';
  position: absolute;
  top: -20%;
  right: -10%;
  width: 500px;
  height: 500px;
  border-radius: 50%;
  background: rgba(79, 70, 229, 0.06);
  filter: blur(80px);
  z-index: 0;
  pointer-events: none;
}

.chat-container::after {
  content: '';
  position: absolute;
  bottom: -15%;
  left: -10%;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: rgba(124, 58, 237, 0.05);
  filter: blur(80px);
  z-index: 0;
  pointer-events: none;
}

/* ── Top Bar ─────────────────────────────────────────── */
.chat-topbar {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  flex-shrink: 0;
  background: transparent;
  position: relative;
  z-index: 1;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 6px;
}

.topbar-text {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-extrabold);
  color: var(--color-text-main);
  letter-spacing: var(--tracking-tight);
  line-height: 1;
  padding-top: 2px;
}

/* ── Body Area ───────────────────────────────────────── */
.chat-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.chat-body.is-empty {
  justify-content: center;
  align-items: center;
  overflow-y: hidden;
}

/* ── Welcome Page (Empty State) ──────────────────────── */
.chat-welcome {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 20px 12px;
  margin-top: -56px;
}

.chat-welcome h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
  letter-spacing: var(--tracking-tight);
  line-height: var(--leading-tight);
}

.chat-welcome p {
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
  margin-bottom: 16px;
  line-height: var(--leading-normal);
  font-weight: var(--font-weight-medium);
}

.quick-questions {
  text-align: center;
  margin-top: 12px;
}

.quick-tag {
  margin: 6px 8px;
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base), background var(--transition-base), border-color var(--transition-base);
  border-radius: var(--radius-full);
  padding: 10px 22px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  box-shadow: var(--shadow-sm);
}

.quick-tag:hover {
  background: var(--gradient-primary);
  color: #fff;
  border-color: transparent;
  transform: translateY(-2px);
  box-shadow: var(--shadow-button);
}

/* ── Messages Area ───────────────────────────────────── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
}

.messages-inner {
  max-width: 900px;
  margin: 0 auto;
  padding: 28px 28px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.message-row {
  display: flex;
  width: 100%;
  animation: fadeInUp 0.4s ease-out both;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.thinking-row {
  animation: fadeInUp 0.3s ease-out both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── Message Bubbles ─────────────────────────────────── */
.message-bubble {
  padding: 16px 22px;
  border-radius: var(--radius-xl);
  font-size: var(--font-size-base);
  line-height: var(--leading-relaxed);
  word-break: break-word;
  max-width: 82%;
  transition: box-shadow var(--transition-base);
}

.message-bubble.user {
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: var(--shadow-button);
}

.message-bubble.assistant {
  background: var(--color-surface);
  color: var(--color-text-main);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-light);
}

.audio-control-bar {
  display: flex;
  align-items: center;
  padding: 4px 0 4px 0;
}

.audio-toggle-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1.5px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
  color: var(--color-primary);
  padding: 0;
}

.audio-toggle-btn:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.25);
  transform: scale(1.1);
}

.audio-toggle-btn:active {
  transform: scale(0.9);
}

.audio-toggle-btn.muted {
  color: var(--color-text-subtle);
  border-color: var(--color-border);
  background: var(--color-bg);
}

.audio-wave-icon {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 14px;
}

.audio-wave-bar {
  width: 2.5px;
  height: 4px;
  border-radius: 1.5px;
  background: var(--color-primary);
  animation: audio-wave-pulse 0.8s ease-in-out infinite alternate;
}

.audio-toggle-btn.muted .audio-wave-bar {
  background: var(--color-text-subtle);
}

@keyframes audio-wave-pulse {
  0% {
    height: 4px;
    opacity: 0.3;
  }
  100% {
    height: 14px;
    opacity: 1;
  }
}

/* ── Thinking Indicator ──────────────────────────────── */
.message-bubble.thinking {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 22px;
}

.thinking-text {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
  white-space: nowrap;
  font-weight: var(--font-weight-medium);
}

.typing-dots {
  display: flex;
  align-items: center;
  gap: 5px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gradient-primary);
  animation: typingBounce 1.4s infinite ease-in-out both;
}

.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

/* ── Input Area ──────────────────────────────────────── */
.chat-input-area {
  padding: 12px 28px 24px;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.quick-mode-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text-subtle);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-family);
  white-space: nowrap;
  flex-shrink: 0;
  transition: all var(--transition-base);
  line-height: 1;
  user-select: none;
  margin-bottom: 2px;
}

.quick-mode-toggle:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.quick-mode-toggle:active:not(:disabled) {
  transform: scale(0.95);
}

.quick-mode-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.quick-mode-toggle.active {
  border-color: var(--color-primary);
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.quick-mode-toggle.active:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.45);
}

.quick-mode-toggle svg {
  flex-shrink: 0;
  fill: none;
}

.quick-mode-toggle.active svg {
  fill: rgba(255, 255, 255, 0.3);
}

.image-upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--color-text-subtle);
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--transition-base);
  padding: 0;
  margin-bottom: 2px;
}

.image-upload-btn:hover {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.image-upload-btn:active {
  transform: scale(0.9);
}

.image-upload-btn.has-images {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.1);
}

.image-preview-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  max-width: 900px;
  margin-bottom: 8px;
  overflow-x: auto;
  padding: 2px 4px;
  scrollbar-width: none;
}

.image-preview-bar::-webkit-scrollbar {
  display: none;
}

.image-preview-item {
  position: relative;
  flex-shrink: 0;
}

.image-preview-thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1.5px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.image-preview-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
  transition: transform var(--transition-fast);
}

.image-preview-remove:hover {
  transform: scale(1.15);
}

.image-preview-remove:active {
  transform: scale(0.9);
}

.input-content-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.inline-image-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0 2px 0;
  overflow-x: auto;
  scrollbar-width: none;
  flex-shrink: 0;
}

.inline-image-bar::-webkit-scrollbar {
  display: none;
}

.inline-image-item {
  position: relative;
  flex-shrink: 0;
}

.inline-image-thumb {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  border: 1.5px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.inline-image-remove {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
  transition: transform var(--transition-fast);
}

.inline-image-remove:hover {
  transform: scale(1.12);
}

.inline-image-remove:active {
  transform: scale(0.9);
}

.message-image-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.message-image-thumb {
  max-width: 120px;
  max-height: 120px;
  border-radius: var(--radius-xs);
  object-fit: cover;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 7px;
  width: 100%;
  max-width: 900px;
  background: var(--color-surface);
  border-radius: var(--radius-full);
  border: 2px solid var(--color-border);
  padding: 8px 8px 8px 12px;
  box-shadow: var(--shadow-card);
  transition: border-color var(--transition-base), box-shadow var(--transition-base), border-radius var(--transition-base);
}

.input-wrapper.is-expanded {
  border-radius: 24px;
}

.input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12), var(--shadow-card);
}

.input-wrapper.voice-active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.16), var(--shadow-card);
}

.voice-hint-overlay {
  position: absolute;
  left: 20px;
  right: 60px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-subtle, #9ca3af);
  font-size: var(--font-size-base);
  pointer-events: none;
  z-index: 2;
}

.voice-wave-overlay {
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 28px;
  pointer-events: none;
  z-index: 2;
}

.voice-wave-bar {
  width: 2px;
  height: 4px;
  border-radius: 1px;
  background: rgba(139, 92, 246, 0.5);
  animation: wave-animation 0.6s ease-in-out infinite alternate;
}

@keyframes wave-animation {
  0% { height: 4px; opacity: 0.2; }
  100% { height: 24px; opacity: 1; }
}

.chat-input :deep(.el-textarea__inner) {
  border: none !important;
  box-shadow: none !important;
  border-radius: var(--radius-full);
  padding: 10px 0 10px 4px;
  font-size: var(--font-size-base);
  line-height: 1.6;
  background: transparent;
  resize: none;
  overflow-y: auto;
  font-family: var(--font-family);
  color: var(--color-text-main);
}

.chat-input :deep(.el-textarea__inner):focus {
  border: none !important;
  box-shadow: none !important;
}

.chat-input :deep(.el-textarea__inner)::placeholder {
  color: var(--color-text-subtle);
  font-weight: var(--font-weight-medium);
}

.chat-input :deep(.el-textarea__inner)::-webkit-scrollbar {
  width: 4px;
}

.chat-input :deep(.el-textarea__inner)::-webkit-scrollbar-track {
  background: transparent;
}

.chat-input :deep(.el-textarea__inner)::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 2px;
}

.chat-input :deep(.el-textarea__inner)::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-subtle);
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--color-border);
  color: var(--color-text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform var(--transition-base), box-shadow var(--transition-base), background var(--transition-base);
  padding: 0;
  position: relative;
  overflow: hidden;
}

.send-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--gradient-primary);
  opacity: 0;
  transition: opacity var(--transition-slow);
  border-radius: 50%;
  z-index: 0;
}

.send-btn:not(:disabled) {
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: var(--shadow-button);
}

.send-btn:not(:disabled):hover {
  transform: scale(1.08);
  box-shadow: var(--shadow-button-hover);
}

.send-btn:not(:disabled):active {
  transform: scale(0.95);
}

.send-btn svg {
  position: relative;
  z-index: 1;
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.stop-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform var(--transition-base), box-shadow var(--transition-base), background var(--transition-base);
  padding: 0;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
}

.stop-btn:hover {
  background: #dc2626;
  transform: scale(1.08);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.45);
}

.stop-btn:active {
  transform: scale(0.95);
}

.input-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-subtle);
  margin-top: 10px;
  text-align: center;
  font-weight: var(--font-weight-medium);
}

/* ── Scrollbar (hidden) ──────────────────────────────── */
.chat-messages,
.chat-body {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.chat-messages::-webkit-scrollbar,
.chat-body::-webkit-scrollbar {
  display: none;
}

/* ── Markdown Styles ─────────────────────────────────── */
.markdown-body :deep(h1) {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  margin: 16px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-main);
}

.markdown-body :deep(h2) {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  margin: 14px 0 8px;
  color: var(--color-text-main);
}

.markdown-body :deep(h3) {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  margin: 12px 0 6px;
  color: var(--color-text-main);
}

.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  margin: 10px 0 6px;
  color: var(--color-text-main);
}

.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p) {
  margin: 6px 0;
  line-height: var(--leading-relaxed);
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(li) {
  margin: 3px 0;
  line-height: var(--leading-relaxed);
}

.markdown-body :deep(strong) {
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(blockquote) {
  margin: 10px 0;
  padding: 10px 16px;
  border-left: 3px solid var(--color-primary);
  background: var(--gradient-subtle);
  color: var(--color-text-muted);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: var(--font-size-sm);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--color-bg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-muted);
}

.markdown-body :deep(tr:nth-child(even)) {
  background: var(--color-bg);
}

.markdown-body :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.markdown-body :deep(a:hover) {
  color: var(--color-primary-hover);
}

.markdown-body :deep(hr) {
  margin: 16px 0;
  border: none;
  border-top: 1px solid var(--color-border);
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-sm);
}

/* ── Code Block ──────────────────────────────────────── */
.markdown-body :deep(.code-block-wrapper) {
  margin: 12px 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #1e293b;
  box-shadow: var(--shadow-sm);
}

.markdown-body :deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #334155;
  border-bottom: 1px solid #475569;
}

.markdown-body :deep(.code-lang-label) {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.markdown-body :deep(.code-copy-btn) {
  font-size: var(--font-size-xs);
  padding: 4px 12px;
  border: 1px solid #475569;
  border-radius: var(--radius-full);
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-family);
}

.markdown-body :deep(.code-copy-btn:hover) {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.markdown-body :deep(pre) {
  margin: 0;
  border-radius: 0;
  overflow-x: auto;
  background: #1e293b;
}

.markdown-body :deep(pre code) {
  display: block;
  padding: 16px 20px;
  font-size: var(--font-size-sm);
  line-height: 1.7;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
  color: #e2e8f0;
}

.markdown-body :deep(.inline-code) {
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  background: var(--gradient-subtle);
  color: var(--color-primary);
  font-size: var(--font-size-sm);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
  font-weight: var(--font-weight-medium);
}
</style>

<style>
.quick-tooltip {
  border-radius: 9999px !important;
  padding: 6px 16px !important;
}
</style>
