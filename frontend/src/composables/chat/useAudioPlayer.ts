import { ref } from 'vue'

let allText = ''
let ttsBuffer = ''
let isStreamComplete = false
const synth = window.speechSynthesis

const audioVolume = ref(1.0)

let voicesReadyPromise: Promise<void> | null = null

function ensureVoicesReady(): Promise<void> {
  if (voicesReadyPromise) return voicesReadyPromise

  const voices = synth.getVoices()
  if (voices.length > 0) {
    voicesReadyPromise = Promise.resolve()
    return voicesReadyPromise
  }

  voicesReadyPromise = new Promise<void>((resolve) => {
    const onVoicesChanged = () => {
      synth.removeEventListener('voiceschanged', onVoicesChanged)
      resolve()
    }
    synth.addEventListener('voiceschanged', onVoicesChanged)
    setTimeout(() => {
      synth.removeEventListener('voiceschanged', onVoicesChanged)
      resolve()
    }, 3000)
  })

  return voicesReadyPromise
}

export function getAudioVolume() {
  return audioVolume.value
}

export function setAudioVolume(volume: number) {
  audioVolume.value = Math.max(0, Math.min(1, volume))
}

function getChineseVoice(): SpeechSynthesisVoice | null {
  const voices = synth.getVoices()
  return voices.find(v => v.lang.startsWith('zh-CN'))
      || voices.find(v => v.lang.startsWith('zh'))
      || null
}

let engineWarmedUp = false

function warmUpEngine(): Promise<void> {
  if (engineWarmedUp) return Promise.resolve()
  engineWarmedUp = true

  return ensureVoicesReady().then(() => {
    const utterance = new SpeechSynthesisUtterance('')
    utterance.volume = 0
    utterance.rate = 1.0

    return new Promise<void>((resolve) => {
      const done = () => resolve()
      utterance.onstart = done
      utterance.onend = done
      utterance.onerror = done
      setTimeout(done, 500)
      synth.speak(utterance)
    })
  })
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
    utterance.volume = audioVolume.value

    const voice = getChineseVoice()
    if (voice) {
      utterance.voice = voice
    }

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

    if (voice) {
      synth.speak(utterance)
    } else {
      ensureVoicesReady().then(() => {
        const retryVoice = getChineseVoice()
        if (retryVoice) {
          utterance.voice = retryVoice
        }
        synth.speak(utterance)
      })
    }
  }

  const initAudioStream = () => {
    console.log('[Audio] 初始化语音')
    synth.cancel()
    allText = ''
    ttsBuffer = ''
    isStreamComplete = false
    isAudioPlaying.value = true
    hasAudio.value = true
    warmUpEngine()
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
    utterance.volume = audioVolume.value

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

    const doSpeak = () => {
      const voice = getChineseVoice()
      if (voice) utterance.voice = voice
      synth.speak(utterance)
    }

    const voice = getChineseVoice()
    if (voice) {
      utterance.voice = voice
      synth.speak(utterance)
    } else {
      ensureVoicesReady().then(doSpeak)
    }
  }

  const setMuted = (muted: boolean) => {
    if (isAudioMuted.value === muted) return
    isAudioMuted.value = muted
    if (muted) {
      synth.cancel()
      isAudioPlaying.value = false
    } else {
      if (!isStreamComplete && ttsBuffer.trim()) {
        isAudioPlaying.value = true
        const remaining = ttsBuffer
        ttsBuffer = ''
        speak(remaining)
      }
    }
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
    hasAudio.value = false
  }

  const stopPlayback = () => {
    console.log('[Audio] 仅停止播放')
    synth.cancel()
    isAudioPlaying.value = false
  }

  return {
    hasAudio,
    isAudioPlaying,
    isAudioMuted,
    setMuted,
    initAudioStream,
    handleAudioChunk,
    togglePlay,
    finishAudio,
    stopPlayback,
    cleanup
  }
}