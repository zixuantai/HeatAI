<template>
  <div class="chat-container" :class="{ 'has-messages': messages.length > 0 }">
    <div class="chat-topbar">
      <div class="topbar-brand">
        <span class="topbar-icon">🔥</span>
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
                v-html="renderMarkdown(msg.content)"
              ></div>
              <div v-else class="message-text">{{ msg.content }}</div>
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
        </div>
      </div>

      <div class="chat-input-area">
        <div class="input-wrapper">
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
              :disabled="loading"
              @click="toggleQuickMode"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
              <span>快速模式</span>
            </button>
          </el-tooltip>
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 6 }"
            placeholder="有问题，尽管问"
            resize="none"
            :disabled="loading"
            class="chat-input"
            @keydown.enter.exact="handleSend"
          />
          <button
            v-if="!loading"
            class="send-btn"
            :disabled="!inputMessage.trim()"
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
            @click="handleStop"
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
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { askStreamApi, stopStream, getSessionDetailApi } from '@/api/chat'
import type { ChatMessage } from '@/types'
import { marked } from 'marked'
import hljs from 'highlight.js'

const props = defineProps<{
  sessionId?: string
}>()

const router = useRouter()

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
const loading = ref(false)
const streamingContent = ref('')
const statusMessage = ref('')
const messages = ref<ChatMessage[]>([])
const messagesContainer = ref<HTMLElement>()
const currentSessionId = ref<string | null>(null)
const quickMode = ref(false)

function toggleQuickMode() {
  quickMode.value = !quickMode.value
  console.log('[快速模式] 切换为:', quickMode.value)
}

const statusTextMap: Record<string, string> = {
  analyzing: '正在分析您的问题...',
  retrieving: '正在检索相关知识...',
  generating: '正在生成回答...',
}

let msgIdCounter = 0
let streamMsgId = ''
let sessionLoadedFromStream = false

const quickQuestions = [
  '暖气不热怎么办？',
  '供暖温度标准是多少？',
  '如何缴纳供暖费？',
  '报修流程是怎样的？'
]

function genId() {
  return `msg_${Date.now()}_${++msgIdCounter}`
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

async function loadSessionMessages(sessionId: string) {
  try {
    const detail = await getSessionDetailApi(sessionId)
    if (detail && detail.messages) {
      messages.value = detail.messages.map(m => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: new Date(m.created_at).getTime()
      }))
      currentSessionId.value = sessionId
      nextTick(() => scrollToBottom())
    }
  } catch {
    ElMessage.error('加载对话记录失败')
  }
}

function handleQuickQuestion(question: string) {
  inputMessage.value = question
  handleSend()
}

onMounted(() => {
  if (props.sessionId) {
    loadSessionMessages(props.sessionId)
  }
})

watch(() => props.sessionId, (newId) => {
  if (newId) {
    if (sessionLoadedFromStream) {
      sessionLoadedFromStream = false
      return
    }
    loadSessionMessages(newId)
  } else {
    messages.value = []
    currentSessionId.value = null
  }
})

function handleStop() {
  stopStream()
  finishStream()
}

function finishStream() {
  if (streamingContent.value) {
    const lastMsg = messages.value.find(m => m.id === streamMsgId)
    if (lastMsg) {
      lastMsg.content = streamingContent.value
    }
  }
  streamingContent.value = ''
  streamMsgId = ''
  statusMessage.value = ''
  loading.value = false
  scrollToBottom()
}

async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content || loading.value) return

  const userMsg: ChatMessage = {
    id: genId(),
    role: 'user',
    content,
    timestamp: Date.now()
  }
  messages.value.push(userMsg)
  inputMessage.value = ''
  scrollToBottom()
  loading.value = true
  streamingContent.value = ''

  streamMsgId = genId()
  let placeholderPushed = false
  console.log('[快速模式] 发送消息时 quickMode.value =', quickMode.value)

  askStreamApi(content, currentSessionId.value, {
    onChunk(text: string) {
      streamingContent.value += text
      if (!placeholderPushed) {
        placeholderPushed = true
        messages.value.push({
          id: streamMsgId,
          role: 'assistant',
          content: streamingContent.value,
          timestamp: Date.now()
        })
      } else {
        const msg = messages.value.find(m => m.id === streamMsgId)
        if (msg) {
          msg.content = streamingContent.value
        }
      }
      scrollToBottom()
    },
    onSessionId(sessionId: string) {
      if (!currentSessionId.value) {
        currentSessionId.value = sessionId
        sessionLoadedFromStream = true
        router.replace(`/chat/${sessionId}`)
      }
    },
    onStatus(status: string) {
      statusMessage.value = statusTextMap[status] || status
    },
    onDone() {
      finishStream()
    },
    onError(error: string) {
      if (!placeholderPushed) {
        loading.value = false
        ElMessage.error(error || '请求失败，请稍后重试')
        return
      }
      const msg = messages.value.find(m => m.id === streamMsgId)
      if (msg) {
        msg.content = streamingContent.value
      }
      streamingContent.value = ''
      streamMsgId = ''
      loading.value = false
      ElMessage.error(error || '请求失败，请稍后重试')
      scrollToBottom()
    }
  }, quickMode.value)
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
  padding: 16px 28px;
  flex-shrink: 0;
  background: transparent;
  position: relative;
  z-index: 1;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-icon {
  width: 36px;
  height: 36px;
  background: var(--gradient-primary);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  line-height: 1;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
}

.topbar-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-extrabold);
  color: var(--color-text-main);
  letter-spacing: var(--tracking-tight);
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
  gap: 10px;
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
  align-self: center;
  transition: all var(--transition-base);
  line-height: 1;
  user-select: none;
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

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  width: 100%;
  max-width: 900px;
  background: var(--color-surface);
  border-radius: var(--radius-full);
  border: 2px solid var(--color-border);
  padding: 8px 8px 8px 20px;
  box-shadow: var(--shadow-card);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12), var(--shadow-card);
}

.chat-input :deep(.el-textarea__inner) {
  border: none !important;
  box-shadow: none !important;
  border-radius: var(--radius-full);
  padding: 10px 0;
  font-size: var(--font-size-base);
  line-height: 1.6;
  background: transparent;
  resize: none;
  overflow: hidden;
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
  display: none;
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
