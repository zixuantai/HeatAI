<template>
  <div class="chat-container" :class="{ 'has-messages': messages.length > 0 }">
    <div class="chat-body">
      <div v-if="messages.length === 0" class="chat-welcome">
        <div class="welcome-logo">
          <div class="welcome-icon">🔥</div>
        </div>
        <h2>欢迎使用 HeatAI 供热智能客服</h2>
        <p>我是您的供热服务助手，可以帮您解答供暖相关问题</p>
        <div class="quick-questions">
          <el-tag
            v-for="q in quickQuestions"
            :key="q"
            class="quick-tag"
            @click="handleQuickQuestion(q)"
          >
            {{ q }}
          </el-tag>
        </div>
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
    </div>

    <div class="chat-input-area">
      <div class="input-wrapper">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 6 }"
          placeholder="请输入您的问题，Enter 发送，Shift+Enter 换行..."
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
      <p class="input-hint">内容由AI生成，仅供参考</p>
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
  })
}
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  font-family: 'Helvetica Neue', 'Helvetica', 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* ========== Body Area (fills space above input) ========== */
.chat-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* ========== Welcome Page (Empty State) ========== */
.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.welcome-logo {
  width: 72px;
  height: 72px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35);
}

.welcome-icon {
  font-size: 36px;
  line-height: 1;
}

.chat-welcome h2 {
  font-size: 26px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 10px;
  letter-spacing: -0.3px;
}

.chat-welcome p {
  font-size: 15px;
  color: #94a3b8;
  margin-bottom: 28px;
  line-height: 1.6;
}

.quick-questions {
  text-align: center;
}

.quick-tag {
  margin: 5px 6px;
  cursor: pointer;
  transition: all 0.25s ease;
  border-radius: 20px;
  padding: 8px 18px;
  font-size: 13px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
}

.quick-tag:hover {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.3);
}

/* ========== Messages Area ========== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
}

.messages-inner {
  max-width: 880px;
  margin: 0 auto;
  padding: 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-row {
  display: flex;
  width: 100%;
  animation: fadeInUp 0.35s ease-out both;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.thinking-row {
  animation: fadeInUp 0.25s ease-out both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ========== Message Bubbles (updated) ========== */
.message-bubble {
  padding: 14px 20px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
  max-width: 85%;
  transition: box-shadow 0.2s ease;
}

.message-bubble.user {
  background: #eef2ff;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.message-bubble.assistant {
  background: #fff;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

/* ========== Thinking Indicator ========== */
.message-bubble.thinking {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
}

.thinking-text {
  font-size: 13px;
  color: #94a3b8;
  white-space: nowrap;
}

.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.typing-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #6366f1;
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

/* ========== Input Area (always at bottom) ========== */
.chat-input-area {
  padding: 12px 24px 16px;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  width: 100%;
  max-width: 880px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  padding: 6px 6px 6px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: #6366f1;
  box-shadow: 0 2px 20px rgba(99, 102, 241, 0.1);
}

.chat-input :deep(.el-textarea__inner) {
  border: none !important;
  box-shadow: none !important;
  padding: 8px 0;
  font-size: 14px;
  line-height: 1.6;
  background: transparent;
  resize: none;
  overflow: hidden;
  font-family: 'Helvetica Neue', 'Helvetica', 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.chat-input :deep(.el-textarea__inner):focus {
  border: none !important;
  box-shadow: none !important;
}

.chat-input :deep(.el-textarea__inner)::placeholder {
  color: #94a3b8;
}

.chat-input :deep(.el-textarea__inner)::-webkit-scrollbar {
  display: none;
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: #e2e8f0;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
  padding: 0;
}

.send-btn:not(:disabled) {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.send-btn:not(:disabled):hover {
  transform: scale(1.06);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45);
}

.send-btn:not(:disabled):active {
  transform: scale(0.96);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.stop-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: #ef4444;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
  padding: 0;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.35);
}

.stop-btn:hover {
  background: #dc2626;
  transform: scale(1.06);
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.45);
}

.stop-btn:active {
  transform: scale(0.96);
}

.input-hint {
  font-size: 11px;
  color: #cbd5e1;
  margin-top: 8px;
  text-align: center;
}

/* ========== Scrollbar (hidden) ========== */
.chat-messages,
.chat-body {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.chat-messages::-webkit-scrollbar,
.chat-body::-webkit-scrollbar {
  display: none;
}

/* ========== Markdown Styles ========== */
.markdown-body :deep(h1) {
  font-size: 20px;
  font-weight: 700;
  margin: 16px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e2e8f0;
}

.markdown-body :deep(h2) {
  font-size: 18px;
  font-weight: 700;
  margin: 14px 0 8px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 12px 0 6px;
}

.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-size: 15px;
  font-weight: 600;
  margin: 10px 0 6px;
}

.markdown-body :deep(h1:first-child),
.markdown-body :deep(h2:first-child),
.markdown-body :deep(h3:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p) {
  margin: 6px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.markdown-body :deep(li) {
  margin: 3px 0;
}

.markdown-body :deep(strong) {
  font-weight: 700;
  color: #1e293b;
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(blockquote) {
  margin: 10px 0;
  padding: 8px 14px;
  border-left: 3px solid #6366f1;
  background: #eef2ff;
  color: #475569;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f1f5f9;
  font-weight: 600;
}

.markdown-body :deep(tr:nth-child(even)) {
  background: #f8fafc;
}

.markdown-body :deep(a) {
  color: #6366f1;
  text-decoration: underline;
}

.markdown-body :deep(a:hover) {
  color: #4f46e5;
}

.markdown-body :deep(hr) {
  margin: 16px 0;
  border: none;
  border-top: 1px solid #e2e8f0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

/* ========== Code Block ========== */
.markdown-body :deep(.code-block-wrapper) {
  margin: 12px 0;
  border: 1.5px solid #cbd5e1;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.markdown-body :deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #e2e8f0;
  border-bottom: 1px solid #cbd5e1;
}

.markdown-body :deep(.code-lang-label) {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

.markdown-body :deep(.code-copy-btn) {
  font-size: 12px;
  padding: 3px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.markdown-body :deep(.code-copy-btn:hover) {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}

.markdown-body :deep(pre) {
  margin: 0;
  border-radius: 0;
  overflow-x: auto;
  background: #f8fafc;
}

.markdown-body :deep(pre code) {
  display: block;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.5;
  font-family: 'Consolas', 'Courier New', monospace;
}

.markdown-body :deep(.inline-code) {
  padding: 2px 6px;
  border-radius: 4px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 13px;
  font-family: 'Consolas', 'Courier New', monospace;
}
</style>
