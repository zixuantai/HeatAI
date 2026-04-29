<template>
  <div class="chat-container">
    <div v-if="messages.length === 0" class="chat-welcome">
      <div class="welcome-icon">🔥</div>
      <h2>欢迎使用 HeatAI 供热智能客服</h2>
      <p>我是您的供热服务助手，可以帮您解答供暖相关问题</p>
      <div class="quick-questions">
        <h4>您可以尝试问我：</h4>
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
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-row"
        :class="msg.role"
      >
        <div v-if="msg.role === 'assistant'" class="message-avatar">
          <el-avatar :size="32" class="bot-avatar">AI</el-avatar>
        </div>
        <div class="message-bubble" :class="msg.role">
          <div
            v-if="msg.role === 'assistant'"
            class="message-text markdown-body"
            v-html="renderMarkdown(msg.content)"
          ></div>
          <div v-else class="message-text">{{ msg.content }}</div>
        </div>
        <div v-if="msg.role === 'user'" class="message-avatar">
          <el-avatar :size="32" icon="UserFilled" class="user-avatar" />
        </div>
      </div>

      <div v-if="loading" class="message-row assistant">
        <div class="message-avatar">
          <el-avatar :size="32" class="bot-avatar">AI</el-avatar>
        </div>
        <div class="message-bubble assistant thinking">
          <span class="dot-pulse"></span>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="2"
        placeholder="请输入您的问题，Enter 发送，Shift+Enter 换行..."
        resize="none"
        :disabled="loading"
        @keydown.enter.exact="handleSend"
      />
      <el-button
        type="primary"
        :disabled="!inputMessage.trim() || loading"
        :loading="loading"
        class="send-btn"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { askApi } from '@/api/chat'
import type { ChatMessage } from '@/types'
import { marked } from 'marked'
import hljs from 'highlight.js'

marked.setOptions({
  breaks: true,
  gfm: true
})

const renderer = new marked.Renderer()
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  const validLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  const highlighted = hljs.highlight(text, { language: validLang }).value
  return `<pre><code class="hljs language-${validLang}">${highlighted}</code></pre>`
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
const messages = ref<ChatMessage[]>([])
const messagesContainer = ref<HTMLElement>()

let msgIdCounter = 0

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

function handleQuickQuestion(question: string) {
  inputMessage.value = question
  handleSend()
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

  try {
    const res = await askApi(content)
    const botMsg: ChatMessage = {
      id: genId(),
      role: 'assistant',
      content: res.answer,
      timestamp: Date.now()
    }
    messages.value.push(botMsg)
  } catch {
    ElMessage.error('请求失败，请稍后重试')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
}

.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.chat-welcome h2 {
  font-size: 24px;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.chat-welcome p {
  font-size: 15px;
  color: #909399;
  margin-bottom: 30px;
}

.quick-questions {
  text-align: center;
}

.quick-questions h4 {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
  font-weight: 500;
}

.quick-tag {
  margin: 4px 6px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 16px;
  padding: 6px 16px;
  font-size: 13px;
}

.quick-tag:hover {
  background-color: #ff6b35;
  color: #fff;
  border-color: #ff6b35;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-row {
  display: flex;
  gap: 10px;
  max-width: 85%;
}

.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-row.assistant {
  align-self: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}

.bot-avatar {
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.user-avatar {
  background: #1a1a2e;
}

.message-bubble {
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.message-bubble.user {
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: #fff;
  color: #303133;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.message-bubble.thinking {
  display: flex;
  align-items: center;
  padding: 14px 20px;
}

.dot-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff6b35;
  animation: dotPulse 1.2s infinite ease-in-out;
}

@keyframes dotPulse {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.chat-input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #ececec;
  background: #fff;
  align-items: flex-end;
}

.send-btn {
  height: 40px;
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  border: none;
  border-radius: 8px;
  padding: 0 24px;
  font-size: 14px;
}

.send-btn:hover {
  background: linear-gradient(135deg, #e55d2b, #e6840e);
}

/* ========== Markdown 渲染样式 ========== */
.markdown-body :deep(h1) {
  font-size: 20px;
  font-weight: 700;
  margin: 16px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e8e8e8;
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
  color: #1a1a2e;
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(blockquote) {
  margin: 10px 0;
  padding: 8px 14px;
  border-left: 3px solid #ff6b35;
  background: #fff7f0;
  color: #666;
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
  border: 1px solid #e0e0e0;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.markdown-body :deep(tr:nth-child(even)) {
  background: #fafafa;
}

.markdown-body :deep(a) {
  color: #ff6b35;
  text-decoration: underline;
}

.markdown-body :deep(a:hover) {
  color: #e55d2b;
}

.markdown-body :deep(hr) {
  margin: 16px 0;
  border: none;
  border-top: 1px solid #e8e8e8;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

.markdown-body :deep(pre) {
  margin: 10px 0;
  border-radius: 8px;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  display: block;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.5;
  font-family: 'Consolas', 'Courier New', monospace;
}

.inline-code {
  padding: 2px 6px;
  border-radius: 4px;
  background: #f0f0f0;
  color: #e55d2b;
  font-size: 13px;
  font-family: 'Consolas', 'Courier New', monospace;
}
</style>
