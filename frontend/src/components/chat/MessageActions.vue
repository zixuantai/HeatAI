<template>
  <div v-if="message.role === 'assistant' && message.content" class="message-actions">
    <button
      class="action-btn"
      :class="{ active: isPlaying }"
      @click="handleVoice"
      :title="isPlaying ? '停止播放' : '语音播放'"
    >
      <svg v-if="isPlaying" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
      </svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      </svg>
    </button>

    <button
      class="action-btn"
      @click="handleCopy"
      :title="'复制内容'"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
      </svg>
    </button>

    <button
      class="action-btn"
      @click="handleSource"
      title="查看来源"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '@/types'
import { useClipboard } from '@/composables/chat/useClipboard'
import { useVoicePlayback } from '@/composables/chat/useVoicePlayback'
import { extractSources } from '@/composables/chat/useSourceExtractor'

const props = defineProps<{
  message: ChatMessage
}>()

const emit = defineEmits<{
  showSource: [sources: ReturnType<typeof extractSources>]
}>()

const { copyText } = useClipboard()
const { isPlaying, speak, stop } = useVoicePlayback()

function handleCopy() {
  const text = stripMarkdownForCopy(props.message.content)
  copyText(text)
}

function handleVoice() {
  if (isPlaying.value) {
    stop()
  } else {
    const text = stripMarkdownForVoice(props.message.content)
    speak(text)
  }
}

function handleSource() {
  const sources = extractSources(props.message.content)
  emit('showSource', sources)
}

function stripMarkdownForCopy(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`{1,3}[^`]*`{1,3}/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^>\s+/gm, '')
    .replace(/^[-*+]\s+/gm, '• ')
    .replace(/^\d+\.\s+/gm, '')
    .trim()
}

function stripMarkdownForVoice(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`{1,3}[^`]*`{1,3}/g, '代码')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^>\s+/gm, '')
    .replace(/^[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    .replace(/\n{2,}/g, '\n')
    .trim()
}
</script>

<style scoped>
.message-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0 0 0;
}

.action-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--color-text-subtle);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-base);
  padding: 0;
}

.action-btn:hover:not(:disabled) {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
}

.action-btn:active:not(:disabled) {
  transform: scale(0.9);
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.action-btn.active:not(:disabled) {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.1);
}
</style>
