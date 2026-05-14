import { ref } from 'vue'

let allText = ''
let ttsBuffer = ''
let isStreamComplete = false
const synth = window.speechSynthesis

function getChineseVoice(): SpeechSynthesisVoice | null {
  const voices = synth.getVoices()
  return voices.find(v => v.lang.startsWith('zh-CN'))
      || voices.find(v => v.lang.startsWith('zh'))
      || null
}

export function useAudioPlayer() {
  const hasAudio = ref(false)
  const isAudioPlaying = ref(false)
  const isAudioMuted = ref(false)

  const speak = (text: string) => {
    if (!text.trim() || isAudioMuted.value) return

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 1.0

    const voice = getChineseVoice()
    if (voice) utterance.voice = voice

    utterance.onstart = () => {
      isAudioPlaying.value = true
    }
    utterance.onend = () => {
      if (!synth.speaking && !synth.pending) {
        isAudioPlaying.value = false
      }
    }
    utterance.onerror = (e) => {
      if (e.error !== 'interrupted') {
        console.error('[Audio] 语音错误:', e.error)
      }
      if (!synth.speaking && !synth.pending) {
        isAudioPlaying.value = false
      }
    }

    synth.speak(utterance)
  }

  const initAudioStream = () => {
    console.log('[Audio] 初始化语音')
    synth.cancel()
    allText = ''
    ttsBuffer = ''
    isStreamComplete = false
    isAudioMuted.value = false
    isAudioPlaying.value = true
    hasAudio.value = true
  }

  const handleAudioChunk = (text: string) => {
    allText += text
    if (isAudioMuted.value) return

    ttsBuffer += text
    const match = ttsBuffer.match(/[。！？!?.\n]/)
    if (match) {
      const idx = match.index! + 1
      const sentence = ttsBuffer.slice(0, idx).trim()
      ttsBuffer = ttsBuffer.slice(idx)
      if (sentence) {
        speak(sentence)
      }
    }
  }

  const finishAudio = () => {
    console.log('[Audio] 流结束, 总文本长度:', allText.length)
    isStreamComplete = true
    if (isAudioMuted.value) {
      isAudioPlaying.value = false
      return
    }
    if (ttsBuffer.trim()) {
      speak(ttsBuffer.trim())
    }
    ttsBuffer = ''
  }

  const replayAudio = () => {
    console.log('[Audio] 开始重播, 文本长度:', allText.length)
    if (!allText.trim()) return

    synth.cancel()
    isAudioMuted.value = false
    isAudioPlaying.value = true

    const utterance = new SpeechSynthesisUtterance(allText)
    utterance.rate = 1.0
    utterance.pitch = 1.0
    utterance.volume = 1.0

    const voice = getChineseVoice()
    if (voice) utterance.voice = voice

    utterance.onend = () => {
      console.log('[Audio] 重播结束')
      isAudioPlaying.value = false
    }
    utterance.onerror = (e) => {
      if (e.error !== 'interrupted') {
        console.error('[Audio] 重播错误:', e.error)
      }
      isAudioPlaying.value = false
    }

    synth.speak(utterance)
  }

  const togglePlay = () => {
    console.log('[Audio] togglePlay, isStreamComplete:', isStreamComplete, 'isAudioPlaying:', isAudioPlaying.value)
    if (!hasAudio.value) return

    if (isStreamComplete) {
      if (isAudioPlaying.value) {
        synth.cancel()
        isAudioPlaying.value = false
      } else {
        replayAudio()
      }
    } else {
      isAudioMuted.value = !isAudioMuted.value
      if (isAudioMuted.value) {
        synth.cancel()
        isAudioPlaying.value = false
      } else {
        isAudioPlaying.value = true
        if (ttsBuffer.trim()) {
          const remaining = ttsBuffer
          ttsBuffer = ''
          speak(remaining)
        }
      }
    }
  }

  const cleanup = () => {
    console.log('[Audio] 完全清理')
    synth.cancel()
    allText = ''
    ttsBuffer = ''
    isStreamComplete = false
    isAudioPlaying.value = false
    isAudioMuted.value = false
    hasAudio.value = false
  }

  return {
    hasAudio,
    isAudioPlaying,
    isAudioMuted,
    initAudioStream,
    handleAudioChunk,
    togglePlay,
    finishAudio,
    cleanup
  }
}