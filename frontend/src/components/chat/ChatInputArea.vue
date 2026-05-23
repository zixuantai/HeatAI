<template>
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
          @click="emit('update:quickMode', !quickMode)"
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
          v-model="inputModel"
          type="textarea"
          :rows="1"
          :autosize="{ minRows: 1, maxRows: 6 }"
          :placeholder="isVoiceMode ? '' : placeholder"
          resize="none"
          class="chat-input"
          :disabled="isVoiceMode"
          @keydown.enter.exact.prevent="emit('send')"
        />
      </div>
      <VoiceInput
        ref="voiceInputRef"
        @send="emit('voice-send', $event)"
        @stop="emit('voice-stop')"
        @update:voiceMode="isVoiceMode = $event"
        @update:isSpeaking="isSpeaking = $event"
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
        :disabled="!inputModel.trim() && uploadedImages.length === 0"
        title="发送消息"
        @click="emit('send')"
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
        @click="emit('stop')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <rect x="4" y="4" width="16" height="16" rx="3" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import type { ElInput } from 'element-plus'
import VoiceInput from '@/components/chat/VoiceInput.vue'
import { useImageUpload } from '@/composables/chat/useImageUpload'

const props = withDefaults(defineProps<{
  modelValue: string
  loading?: boolean
  quickMode?: boolean
  placeholder?: string
}>(), {
  loading: false,
  quickMode: false,
  placeholder: '有问题，尽管问',
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'update:quickMode', val: boolean): void
  (e: 'send'): void
  (e: 'stop'): void
  (e: 'voice-send', text: string): void
  (e: 'voice-stop'): void
}>()

const inputModel = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const inputRef = ref<InstanceType<typeof ElInput>>()
const fileInputRef = ref<HTMLInputElement>()
const voiceInputRef = ref()
const isVoiceMode = ref(false)
const isSpeaking = ref(false)
const isMultiLine = ref(false)

const { uploadedImages, handleImageSelect, handlePaste, removeImage } = useImageUpload()

function triggerImageUpload() {
  fileInputRef.value?.click()
}

// Watch input changes to detect multiline
watch(inputModel, () => {
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

defineExpose({ inputRef, fileInputRef, voiceInputRef, uploadedImages, triggerImageUpload, focus: () => inputRef.value?.focus() })
</script>