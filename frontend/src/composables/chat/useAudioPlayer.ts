import { ref, watch } from 'vue'

const audioVolume = ref(1.0)

export function getAudioVolume() {
  return audioVolume.value
}

export function setAudioVolume(volume: number) {
  audioVolume.value = Math.max(0, Math.min(1, volume))
  if (currentAudio) {
    currentAudio.volume = audioVolume.value
  }
}

let audioChunks: string[] = []
let currentAudio: HTMLAudioElement | null = null
let isComplete = false

export function useAudioPlayer() {
  const hasAudio = ref(false)
  const isAudioPlaying = ref(false)
  const isAudioMuted = ref(false)

  function createAndPlayAudio(b64Chunks: string[]) {
    if (b64Chunks.length === 0) return null

    const combined = b64Chunks.join('')
    console.log('[Audio] 创建Audio, 总base64长度:', combined.length)

    const audio = new Audio(`data:audio/mp3;base64,${combined}`)
    audio.volume = audioVolume.value
    audio.preload = 'auto'

    const doPlay = () => {
      console.log('[Audio] 开始播放, readyState:', audio.readyState)
      audio.play().then(() => {
        console.log('[Audio] play() 成功')
      }).catch((e) => {
        console.error('[Audio] play() 失败:', e.name, e.message)
        stopCurrent(audio)
      })
    }

    audio.onended = () => {
      console.log('[Audio] 播放结束')
      stopCurrent(audio)
      isAudioPlaying.value = false
    }

    audio.onerror = () => {
      const err = audio.error
      console.error('[Audio] 加载失败, code:', err?.code, 'message:', err?.message)
      stopCurrent(audio)
      isAudioPlaying.value = false
    }

    // data: URL 可能瞬间加载完毕，readyState >= 2 表示可直接播放
    if (audio.readyState >= 2) {
      doPlay()
    } else {
      audio.oncanplaythrough = doPlay
      // 兜底：5秒后如果还没播放就强制尝试
      setTimeout(() => {
        if (currentAudio === audio && audio.readyState >= 1 && audio.paused) {
          console.log('[Audio] 兜底触发播放')
          doPlay()
        }
      }, 5000)
    }

    return audio
  }

  function stopCurrent(audio: HTMLAudioElement | null = null) {
    if (audio && currentAudio === audio) {
      currentAudio = null
    }
  }

  const initAudioStream = () => {
    console.log('[Audio] initAudioStream - 初始化音频接收')
    stopAllAudio()
    audioChunks = []
    isComplete = false
    isAudioPlaying.value = true
    hasAudio.value = true
  }

  const handleServerAudio = (audioBase64: string) => {
    console.log('[Audio] handleServerAudio 收到片段, 长度:', audioBase64.length)
    if (isAudioMuted.value) {
      console.log('[Audio] 已静音, 跳过')
      return
    }
    audioChunks.push(audioBase64)
  }

  const handleAudioChunk = (_text: string) => {
    // 不再使用浏览器 speechSynthesis，改为播放服务端音频
  }

  const finishAudio = () => {
    console.log('[Audio] finishAudio - 片段数:', audioChunks.length, '静音:', isAudioMuted.value)
    isComplete = true

    if (isAudioMuted.value) {
      console.log('[Audio] 静音状态, 不播放')
      isAudioPlaying.value = false
      return
    }

    if (audioChunks.length === 0) {
      console.log('[Audio] 无音频片段, 不播放')
      isAudioPlaying.value = false
      return
    }

    // 自动播放：确保状态为播放中
    isAudioMuted.value = false
    isAudioPlaying.value = true

    const audio = createAndPlayAudio([...audioChunks])
    if (audio) {
      currentAudio = audio
    }
  }

  const replayAudio = () => {
    console.log('[Audio] replayAudio - 片段数:', audioChunks.length)
    if (audioChunks.length === 0) return

    stopAllAudio()
    isAudioMuted.value = false
    isAudioPlaying.value = true

    const audio = createAndPlayAudio([...audioChunks])
    if (audio) {
      currentAudio = audio
    }
  }

  const setMuted = (muted: boolean) => {
    if (isAudioMuted.value === muted) return
    isAudioMuted.value = muted
    if (muted) {
      stopAllAudio()
      isAudioPlaying.value = false
    }
  }

  const togglePlay = () => {
    console.log('[Audio] togglePlay, currentAudio:', !!currentAudio, 'paused:', currentAudio?.paused, 'chunks:', audioChunks.length, 'isComplete:', isComplete)
    if (!hasAudio.value) return

    if (currentAudio) {
      if (currentAudio.paused) {
        currentAudio.play().catch(() => {})
        isAudioPlaying.value = true
        isAudioMuted.value = false
      } else {
        currentAudio.pause()
        isAudioPlaying.value = false
        isAudioMuted.value = true
      }
    } else if (audioChunks.length > 0) {
      // 音频已收集完毕，重新播放
      isAudioMuted.value = false
      isAudioPlaying.value = true
      const audio = createAndPlayAudio([...audioChunks])
      if (audio) {
        currentAudio = audio
      }
    } else if (!isComplete) {
      // 流式阶段：音频尚未到达，切换静音状态
      if (isAudioMuted.value) {
        isAudioMuted.value = false
        isAudioPlaying.value = true
        console.log('[Audio] 取消静音，等待音频到达')
      } else {
        isAudioMuted.value = true
        isAudioPlaying.value = false
        console.log('[Audio] 静音，将丢弃后续音频')
      }
    }
  }

  const cleanup = () => {
    console.log('[Audio] cleanup')
    stopAllAudio()
    audioChunks = []
    isComplete = false
    isAudioPlaying.value = false
    hasAudio.value = false
  }

  /**
   * 从外部加载音频数据（如历史对话），准备播放
   */
  const loadSessionAudio = (chunks: string[]) => {
    console.log('[Audio] loadSessionAudio - 加载', chunks.length, '个片段')
    stopAllAudio()
    audioChunks = [...chunks]
    isComplete = true
    isAudioMuted.value = false
    isAudioPlaying.value = false
    hasAudio.value = chunks.length > 0
  }

  const unloadAudio = () => {
    console.log('[Audio] unloadAudio - 卸载音频，保留 store 数据')
    stopAllAudio()
    audioChunks = []
    isComplete = false
    isAudioPlaying.value = false
    hasAudio.value = false
  }

  const stopPlayback = () => {
    console.log('[Audio] stopPlayback')
    stopAllAudio()
    isAudioPlaying.value = false
  }

  function stopAllAudio() {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
      currentAudio = null
    }
  }

  watch(audioVolume, (vol) => {
    if (currentAudio) {
      currentAudio.volume = vol
    }
  })

  return {
    hasAudio,
    isAudioPlaying,
    isAudioMuted,
    setMuted,
    initAudioStream,
    loadSessionAudio,
    unloadAudio,
    handleAudioChunk,
    handleServerAudio,
    togglePlay,
    finishAudio,
    stopPlayback,
    cleanup
  }
}