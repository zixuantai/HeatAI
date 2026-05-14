<template>
  <div class="voice-input-wrapper">
    <button
      class="voice-toggle-btn"
      :class="{ active: isVoiceMode, listening: isListening }"
      :title="isVoiceMode ? '切换为文字输入' : '语音输入'"
      @click="toggleVoiceMode"
    >
      <svg
        width="22" height="22" viewBox="0 0 24 24"
        fill="none" stroke="currentColor"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      >
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
    </button>
    <div v-if="voiceError" class="voice-error">{{ voiceError }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { MicVAD, utils } from '@ricky0123/vad-web'
import { stopVoiceStream } from '@/api/chat'

const emit = defineEmits<{
  (e: 'send', audioBase64: string): void
  (e: 'stop'): void
  (e: 'update:voiceMode', value: boolean): void
  (e: 'update:isSpeaking', value: boolean): void
}>()

const isVoiceMode = ref(false)
const isListening = ref(false)
const isSpeaking = ref(false)
const voiceError = ref('')

let vad: any = null

async function initVAD() {
  try {
    vad = await MicVAD.new({
      baseAssetPath: '/vad/',
      onnxWASMBasePath: '/node_modules/onnxruntime-web/dist/',
      model: 'legacy',
      startOnLoad: false,
      positiveSpeechThreshold: 0.5,
      negativeSpeechThreshold: 0.35,
      redemptionMs: 500,
      preSpeechPadMs: 150,
      minSpeechMs: 300,
      submitUserSpeechOnPause: false,
      getStream: () => navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      }),
      onSpeechStart: () => {
        isSpeaking.value = true
        emit('update:isSpeaking', true)
      },
      onVADMisfire: () => {
        isSpeaking.value = false
        emit('update:isSpeaking', false)
      },
      onSpeechEnd: async (audio: Float32Array) => {
        isSpeaking.value = false
        emit('update:isSpeaking', false)

        console.log('[Voice] 语音结束, 音频长度:', audio.length, '采样数')

        try {
          const wavBuffer = utils.encodeWAV(audio, 1, 16000, 1, 16)
          console.log('[Voice] WAV编码完成, 大小:', wavBuffer.byteLength, 'bytes')
          const base64 = utils.arrayBufferToBase64(wavBuffer)
          console.log('[Voice] Base64编码完成, 长度:', base64.length)
          emit('send', base64)
        } catch (err) {
          console.error('[Voice] 音频编码失败:', err)
          voiceError.value = '音频处理失败，请重试'
        }
      },
      onFrameProcessed: () => {}
    })

    await vad.start()
    isListening.value = true
    voiceError.value = ''
    console.log('[Voice] VAD初始化成功，开始监听')
  } catch (err: any) {
    console.error('[Voice] VAD初始化失败:', err)
    const msg = err?.message || String(err)
    console.error('[Voice] 错误详情:', msg)
    if (msg.includes('Permission') || msg.includes('NotAllowed') || msg.includes('permission')) {
      voiceError.value = '请允许麦克风权限后重试'
    } else if (msg.includes('NotSupported') || msg.includes('device') || msg.includes('NotFound')) {
      voiceError.value = '未检测到麦克风设备'
    } else if (msg.includes('fetch') || msg.includes('network') || msg.includes('Network')) {
      voiceError.value = '网络异常，请检查连接'
    } else {
      voiceError.value = msg.length > 40 ? '语音服务初始化失败' : msg
    }
    isVoiceMode.value = false
    isListening.value = false
    emit('update:voiceMode', false)
    vad = null
  }
}

async function enableVoiceMode() {
  isVoiceMode.value = true
  voiceError.value = ''
  emit('update:voiceMode', true)
  await initVAD()
}

async function disableVoiceMode() {
  if (vad) {
    try {
      await vad.destroy()
    } catch { /* ignore */ }
    vad = null
  }
  isVoiceMode.value = false
  isListening.value = false
  isSpeaking.value = false
  voiceError.value = ''
  emit('update:voiceMode', false)
  emit('update:isSpeaking', false)
}

async function toggleVoiceMode() {
  if (isVoiceMode.value) {
    await disableVoiceMode()
  } else {
    await enableVoiceMode()
  }
}

function handleStop() {
  stopVoiceStream()
  isSpeaking.value = false
  emit('update:isSpeaking', false)
  emit('stop')
}

function pauseVAD() {
  if (vad) {
    try {
      vad.pause()
      console.log('[Voice] VAD已暂停')
    } catch (err) {
      console.warn('[Voice] VAD暂停失败:', err)
    }
  }
}

function resumeVAD() {
  if (vad) {
    try {
      vad.start()
      console.log('[Voice] VAD已恢复')
    } catch (err) {
      console.warn('[Voice] VAD恢复失败:', err)
    }
  }
}

defineExpose({
  disableVoiceMode,
  handleStop,
  pauseVAD,
  resumeVAD
})

onUnmounted(async () => {
  if (vad) {
    try {
      await vad.destroy()
    } catch { /* ignore */ }
    vad = null
  }
})
</script>

<style scoped>
.voice-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.voice-toggle-btn {
  width: 44px;
  height: 44px;
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

.voice-toggle-btn:hover {
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.08);
}

.voice-toggle-btn.active {
  background: var(--gradient-primary);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.voice-toggle-btn.active:hover {
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.45);
}

.voice-toggle-btn.listening {
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.2);
}

.voice-error {
  font-size: var(--font-size-xs);
  color: #ef4444;
  white-space: nowrap;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>