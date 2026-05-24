<template>
  <div class="chat-page-wrapper" :class="{ 'panel-open': sourcePanelVisible }">
    <div class="chat-container" :class="{ 'has-messages': messages.length > 0 }">
      <div class="chat-topbar">
        <button class="back-btn" @click="router.push('/plaza')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          <span>返回知识库广场</span>
        </button>
        <div class="topbar-actions">
          <button
            class="new-chat-btn"
            title="基于当前知识库开启新对话"
            @click="handleNewChat"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>新建对话</span>
          </button>
        </div>
      </div>

      <div class="chat-body" :class="{ 'is-empty': messages.length === 0 }">
        <div v-if="messages.length === 0" class="kb-welcome">
          <div v-if="loadingKb" class="kb-welcome-loading">
            <span class="loading-spinner"></span>
          </div>
          <div v-else-if="kbInfo" class="kb-welcome-content">
            <div class="kb-avatar-area">
              <div class="kb-avatar" :style="kbInfo.avatar ? {} : { background: kbInfo.cover_color || 'var(--gradient-primary)' }">
                <img v-if="kbInfo.avatar" :src="kbInfo.avatar" alt="知识库头像" class="kb-avatar-img" />
                <span v-else class="kb-avatar-text">{{ kbInfo.name.charAt(0) }}</span>
              </div>
            </div>
            <h2 class="kb-name">{{ kbInfo.name }}</h2>
            <div class="kb-desc-wrap" :class="{ expanded: descExpanded }">
              <p v-if="kbInfo.description" ref="descRef" class="kb-desc">{{ kbInfo.description }}</p>
              <button
                v-if="descOverflow"
                class="desc-toggle"
                @click="descExpanded = !descExpanded"
              >
                {{ descExpanded ? '▲' : '▼' }}
              </button>
            </div>
            <div class="kb-creator-info">
              <img
                v-if="ownerAvatarIsImage && kbInfo.owner_avatar"
                :src="kbInfo.owner_avatar || ''"
                class="creator-avatar-small"
                alt="创建者头像"
              />
              <span v-else class="creator-avatar-small" :style="ownerAvatarGradientStyle">{{ (kbInfo.owner_name || kbInfo.name).charAt(0) }}</span>
              <span class="creator-name">{{ kbInfo.owner_name || '未知用户' }}</span>
              <span class="meta-divider">|</span>
              <span class="member-count-text">{{ kbInfo.member_count || 0 }}人已加入</span>
            </div>
            <div v-if="!isOwner && !isJoined" class="kb-join-area">
              <button class="join-btn" @click="handleToggleJoin">
                <span>{{ joinLoading ? '处理中...' : '加入知识库' }}</span>
              </button>
            </div>
            <div v-else-if="isJoined" class="kb-join-status">
              <span class="joined-badge">已加入</span>
              <button class="leave-btn-text" @click="handleToggleJoin">退出</button>
            </div>
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
              <div class="message-content">
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
                <MessageActions
                  :message="msg"
                  :is-streaming="streamLoading && msg.role === 'assistant' && index === lastAssistantIndex"
                  @show-source="handleShowSource"
                />
              </div>
            </div>

            <div v-if="streamLoading && streamContent === ''" class="message-row assistant thinking-row">
              <div class="message-bubble assistant thinking">
                <span class="thinking-text">{{ streamStatus || '正在思考' }}</span>
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
              @click="quickMode = !quickMode"
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
              :placeholder="isVoiceMode ? '' : inputPlaceholder"
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
            v-if="!streamLoading"
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
            @click="handleStop"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <rect x="4" y="4" width="16" height="16" rx="3" />
            </svg>
          </button>
        </div>
        <div v-if="messages.length === 0 && displayQuickQuestions.length > 0" class="quick-questions-bottom">
          <el-tag
            v-for="q in displayQuickQuestions"
            :key="q"
            class="quick-tag"
            @click="handleQuickQuestion(q)"
          >
            {{ q }}
          </el-tag>
        </div>
        <BottomCards v-if="messages.length === 0" variant="kbChat" />
        <p v-if="messages.length > 0" class="input-hint">内容由AI生成，仅供参考</p>
      </div>
      </div>
    </div>

    <Transition name="source-slide">
      <SourcePanel
        v-if="sourcePanelVisible"
        :sources="currentSources"
        @close="sourcePanelVisible = false"
      />
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ElInput } from 'element-plus'
import { getSessionDetailApi } from '@/api/chat'
import { getKnowledgeBaseApi, toggleJoinApi } from '@/api/knowledgeBases'
import type { KnowledgeBase, ChatMessage } from '@/types'
import { useAuthStore } from '@/store/modules/auth'
import { useChatStore } from '@/store/modules/chat'
import MessageActions from '@/components/chat/MessageActions.vue'
import SourcePanel from '@/components/chat/SourcePanel.vue'
import VoiceInput from '@/components/chat/VoiceInput.vue'
import BottomCards from '@/components/chat/BottomCards.vue'
import { renderMarkdownCached } from '@/composables/chat/useMarkdown'
import type { SourceItem } from '@/composables/chat/useSourceExtractor'
import { useImageUpload } from '@/composables/chat/useImageUpload'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()

const NEW_SESSION_KEY = '__new__'

const kbId = computed(() => route.params.kbId as string)
const sessionId = computed(() => (route.query.sessionId as string) || null)

const kbInfo = ref<KnowledgeBase | null>(null)
const loadingKb = ref(false)
const inputMessage = ref('')
const inputRef = ref<InstanceType<typeof ElInput>>()
const messagesContainer = ref<HTMLElement>()
const streamCreatedSessionId = ref<string | null>(null)

const sourcePanelVisible = ref(false)
const currentSources = ref<SourceItem[]>([])

const storeKey = computed(() => sessionId.value || NEW_SESSION_KEY)

const quickMode = ref(false)
const isVoiceMode = ref(false)
const isSpeaking = ref(false)
const isMultiLine = ref(false)
const fileInputRef = ref<HTMLInputElement>()
const voiceInputRef = ref()
const joinLoading = ref(false)

const { uploadedImages, handleImageSelect: _handleImageSelect, handlePaste: _handlePaste, removeImage: _removeImage } = useImageUpload()

const descRef = ref<HTMLParagraphElement>()
const descExpanded = ref(false)
const descOverflow = ref(false)

const inputPlaceholder = computed(() => {
  if (!kbInfo.value) return '有问题，尽管问'
  if (isOwner.value || isJoined.value) return '有问题，尽管问'
  return '未加入知识库，可体验问答3次'
})

const ownerAvatarIsImage = computed(() => {
  const av = kbInfo.value?.owner_avatar
  if (!av) return false
  return av.startsWith('http') || av.startsWith('data:') || av.startsWith('/')
})

const ownerAvatarGradientStyle = computed(() => {
  const av = kbInfo.value?.owner_avatar
  if (!av) return {}
  return { background: av }
})

const isOwner = computed(() => {
  if (!kbInfo.value || !authStore.user) return false
  return kbInfo.value.owner_id === authStore.user.id
})

const isJoined = computed(() => {
  return kbInfo.value?.is_joined || false
})

const quickQuestions = computed(() => {
  if (!kbInfo.value?.quick_questions?.length) return []
  return kbInfo.value.quick_questions.slice(0, 4)
})

const displayQuickQuestions = computed(() => quickQuestions.value)

const messages = computed(() => {
  const s = chatStore.sessions[storeKey.value]
  return s ? s.messages : []
})

const lastAssistantIndex = computed(() => {
  const msgs = messages.value
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant') return i
  }
  return -1
})

const streamLoading = computed(() => {
  const s = chatStore.sessions[storeKey.value]
  return s ? s.loading : false
})

const streamContent = computed(() => {
  const s = chatStore.sessions[storeKey.value]
  return s ? s.streamingContent : ''
})

const streamStatus = computed(() => {
  const s = chatStore.sessions[storeKey.value]
  return s ? s.statusMessage : ''
})

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

let pendingScrollRafId: number | null = null
function scheduleScrollToBottom() {
  if (pendingScrollRafId !== null) return
  pendingScrollRafId = requestAnimationFrame(() => {
    pendingScrollRafId = null
    scrollToBottom()
  })
}

watch(streamContent, (newVal) => {
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

function triggerImageUpload() {
  fileInputRef.value?.click()
}

async function handleImageSelect(e: Event) {
  _handleImageSelect(e, focusInput)
}

async function handlePaste(e: ClipboardEvent) {
  _handlePaste(e, focusInput)
}

function removeImage(idx: number) {
  _removeImage(idx)
}

function onVoiceModeChange(val: boolean) {
  isVoiceMode.value = val
}

function onSpeakingChange(val: boolean) {
  isSpeaking.value = val
}

function handleVoiceSend(text: string) {
  inputMessage.value = text
  handleSend()
}

function handleVoiceStop() {
  // Voice stopped
}

async function loadKbInfo() {
  if (!kbId.value) return
  loadingKb.value = true
  try {
    kbInfo.value = await getKnowledgeBaseApi(kbId.value)
    await nextTick()
    checkDescOverflow()
  } catch {
    ElMessage.error('加载知识库信息失败')
  } finally {
    loadingKb.value = false
  }
}

function checkDescOverflow() {
  if (!descRef.value) return
  const el = descRef.value
  descOverflow.value = el.scrollHeight > el.clientHeight + 2
}

function handleShowSource(sources: SourceItem[]) {
  if (sourcePanelVisible.value) {
    sourcePanelVisible.value = false
    return
  }
  currentSources.value = sources
  sourcePanelVisible.value = true
}

function handleStop() {
  chatStore.stopStreamForSession(storeKey.value)
}

function handleNewChat() {
  inputMessage.value = ''
  uploadedImages.value = []
  quickMode.value = false
  router.replace({ path: `/plaza/${kbId.value}/chat` })
}

async function handleToggleJoin() {
  if (!kbInfo.value || joinLoading.value) return
  joinLoading.value = true
  try {
    const resp: any = await toggleJoinApi(kbId.value)
    if (kbInfo.value) {
      kbInfo.value.is_joined = resp.data.is_joined
      if (resp.data.member_count !== undefined) {
        kbInfo.value.member_count = resp.data.member_count
      }
    }
    ElMessage.success(resp.data.is_joined ? '已加入知识库' : '已退出知识库')
  } catch {
    ElMessage.error('操作失败')
  } finally {
    joinLoading.value = false
  }
}

async function loadSessionMessages(sid: string) {
  const existing = chatStore.sessions[sid]
  if (existing && (existing.messages.length > 0 || existing.loading)) {
    nextTick(() => scrollToBottom())
    return
  }

  try {
    const detail = await getSessionDetailApi(sid)
    if (detail && detail.messages) {
      const msgs: ChatMessage[] = detail.messages.map(m => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: new Date(m.created_at).getTime()
      }))
      const cur = chatStore.sessions[sid]
      if (cur && (cur.loading || cur.messages.length > 0)) {
        return
      }
      chatStore.initSession(sid, msgs)
      nextTick(() => scrollToBottom())
    }
  } catch {
    ElMessage.error('加载对话记录失败')
  }
}

function handleQuickQuestion(question: string) {
  if (!authStore.isAuthenticated) {
    sessionStorage.setItem('pending_question', question)
    router.push({ name: 'Login', query: { redirect: route.fullPath } })
    return
  }
  inputMessage.value = question
  handleSend()
}

async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content && uploadedImages.value.length === 0) return
  if (!content && uploadedImages.value.length > 0) {
    inputMessage.value = '请描述这张图片'
  }

  if (!authStore.isAuthenticated) {
    sessionStorage.setItem('pending_question', content || inputMessage.value)
    router.push({ name: 'Login', query: { redirect: route.fullPath } })
    return
  }

  if (streamLoading.value) {
    handleStop()
    return
  }

  const sid = storeKey.value
  const state = chatStore.getOrCreate(sid)
  const images = [...uploadedImages.value]
  const finalContent = inputMessage.value.trim() || content

  const userMsg: ChatMessage = {
    id: genId(),
    role: 'user',
    content: finalContent,
    images: images.length > 0 ? images : undefined,
    timestamp: Date.now()
  }

  state.messages.push(userMsg)

  inputMessage.value = ''
  uploadedImages.value = []
  quickMode.value = false
  focusInput()
  scrollToBottom()

  chatStore.startStream(
    sid,
    sessionId.value || null,
    finalContent,
    images,
    quickMode.value,
    undefined,
    undefined,
    (newSessionId: string) => {
      if (!sessionId.value) {
        streamCreatedSessionId.value = newSessionId
        router.replace({ path: `/plaza/${kbId.value}/chat`, query: { sessionId: newSessionId } })
      }
    },
    (error: string) => {
      ElMessage.error(error || '请求失败，请稍后重试')
    },
    undefined,
    kbId.value || null
  )
}

onMounted(() => {
  const pendingQuestion = sessionStorage.getItem('pending_question')
  if (pendingQuestion) {
    inputMessage.value = pendingQuestion
    sessionStorage.removeItem('pending_question')
  }

  loadKbInfo()

  if (sessionId.value) {
    const existing = chatStore.sessions[sessionId.value]
    if (existing && (existing.messages.length > 0 || existing.loading)) {
      nextTick(() => scrollToBottom())
    } else {
      loadSessionMessages(sessionId.value)
    }
  } else {
    focusInput()
  }
})

onBeforeUnmount(() => {
  if (pendingScrollRafId !== null) {
    cancelAnimationFrame(pendingScrollRafId)
    pendingScrollRafId = null
  }
})

watch(sessionId, (newId, oldId) => {
  if (streamCreatedSessionId.value && newId === streamCreatedSessionId.value) {
    streamCreatedSessionId.value = null
    return
  }

  inputMessage.value = ''
  uploadedImages.value = []
  quickMode.value = false

  if (newId) {
    const existing = chatStore.sessions[newId]
    if (existing && (existing.messages.length > 0 || existing.loading)) {
      nextTick(() => scrollToBottom())
      return
    }
    loadSessionMessages(newId)
  } else {
    focusInput()
  }
})
</script>

<style scoped>
.chat-page-wrapper {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

.source-slide-enter-active,
.source-slide-leave-active {
  transition: width 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94), opacity 0.25s ease;
  overflow: hidden;
}

.source-slide-enter-from,
.source-slide-leave-to {
  width: 0 !important;
  opacity: 0;
}

.source-slide-enter-to,
.source-slide-leave-from {
  width: 420px;
  opacity: 1;
}

.chat-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  font-family: var(--font-family);
  -webkit-font-smoothing: antialiased;
  position: relative;
  overflow: hidden;
}

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

.chat-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  flex-shrink: 0;
  background: transparent;
  position: relative;
  z-index: 10;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family);
  border-radius: var(--radius-full);
  transition: all var(--transition-base);
  white-space: nowrap;
}

.back-btn:hover {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.back-btn:active {
  transform: scale(0.97);
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-main);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family);
  border-radius: var(--radius-full);
  transition: all var(--transition-base);
  white-space: nowrap;
  flex-shrink: 0;
}

.new-chat-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.new-chat-btn:active {
  transform: scale(0.97);
}

.topbar-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  letter-spacing: var(--tracking-tight);
}

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
  padding-top: 2vh;
}

.kb-welcome {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 20px 12px;
  gap: 20px;
}

.kb-welcome-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.kb-welcome-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.kb-avatar-area {
  margin-bottom: 8px;
}

.kb-avatar {
  width: 88px;
  height: 88px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-shadow: var(--shadow-card);
  background: var(--gradient-primary);
}

.kb-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.kb-avatar-text {
  font-size: 40px;
  font-weight: var(--font-weight-extrabold);
  color: #fff;
  line-height: 1;
}

.kb-name {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-extrabold);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: var(--tracking-tight);
  line-height: var(--leading-tight);
  margin: 0;
}

.kb-desc-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  max-width: 560px;
  width: 100%;
}

.kb-desc {
  font-size: var(--font-size-md);
  color: var(--color-text-muted);
  margin: 0;
  line-height: var(--leading-normal);
  font-weight: var(--font-weight-medium);
  text-align: center;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  word-break: break-all;
}

.kb-desc-wrap.expanded .kb-desc {
  display: block;
  -webkit-line-clamp: unset;
  overflow: visible;
}

.desc-toggle {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 8px;
  line-height: 1;
  transition: color var(--transition-base);
}

.desc-toggle:hover {
  color: var(--color-primary);
}

.kb-creator-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.creator-avatar-small {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: #fff;
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

img.creator-avatar-small {
  background: none;
  object-fit: cover;
}

.creator-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.meta-divider {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.member-count-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.kb-join-area {
  margin-top: 4px;
}

.join-btn {
  display: inline-flex;
  align-items: center;
  padding: 10px 28px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--gradient-primary);
  color: #fff;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-button);
}

.join-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-button-hover);
}

.join-btn:active {
  transform: scale(0.97);
}

.join-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.kb-join-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.joined-badge {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
  background: rgba(79, 70, 229, 0.1);
  padding: 4px 14px;
  border-radius: var(--radius-full);
}

.leave-btn-text {
  border: none;
  background: none;
  color: var(--color-text-subtle);
  font-size: var(--font-size-sm);
  cursor: pointer;
  font-family: var(--font-family);
  padding: 0;
}

.leave-btn-text:hover {
  color: var(--color-error);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
}

.messages-inner {
  max-width: 900px;
  margin: 0 auto;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.message-row {
  display: flex;
  width: 100%;
  animation: fadeInUp 0.4s ease-out both;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 82%;
}

.message-row.user .message-content {
  align-items: flex-end;
}

.message-row.assistant .message-content {
  align-items: flex-start;
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

.message-bubble {
  padding: 16px 22px;
  border-radius: var(--radius-xl);
  font-size: var(--font-size-base);
  line-height: var(--leading-relaxed);
  word-break: break-word;
  width: auto;
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

/* ---------- Input Area (100% match Chat.vue) ---------- */
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
  font-weight: var(--font-weight-medium);
  pointer-events: none;
  z-index: 1;
}

.voice-wave-overlay {
  position: absolute;
  left: 20px;
  right: 60px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  pointer-events: none;
  z-index: 1;
}

.voice-wave-bar {
  width: 3px;
  height: 12px;
  background: var(--color-primary);
  border-radius: 2px;
  animation: voiceWave 1.2s ease-in-out infinite;
}

@keyframes voiceWave {
  0%, 100% { height: 4px; opacity: 0.4; }
  50% { height: 16px; opacity: 1; }
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
}

.stop-btn:hover {
  background: #dc2626;
  transform: scale(1.08);
}

.stop-btn:active {
  transform: scale(0.95);
}

.quick-questions-bottom {
  text-align: center;
  margin-top: 12px;
}

.quick-tag {
  margin: 4px 6px;
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base), background var(--transition-base), border-color var(--transition-base);
  border-radius: var(--radius-full);
  padding: 8px 20px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.quick-tag:hover {
  border-color: var(--color-primary);
  background: var(--gradient-primary);
  color: #fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
}

.input-hint {
  margin: 0;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-subtle);
  text-align: center;
}

/* ── Markdown Body (same as Chat.vue) ──────────────────── */
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