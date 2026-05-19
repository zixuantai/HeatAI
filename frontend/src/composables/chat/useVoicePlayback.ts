import { ref } from 'vue'

export function useVoicePlayback() {
  const isPlaying = ref(false)
  const synth = window.speechSynthesis

  function getChineseVoice(): SpeechSynthesisVoice | null {
    const voices = synth.getVoices()
    return voices.find(v => v.lang.startsWith('zh-CN'))
        || voices.find(v => v.lang.startsWith('zh'))
        || null
  }

  function speak(text: string) {
    if (!text.trim()) return

    if (synth.speaking || synth.pending) {
      synth.cancel()
      isPlaying.value = false
      return
    }

    isPlaying.value = true

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.0
    utterance.pitch = 1.0

    const voice = getChineseVoice()
    if (voice) utterance.voice = voice

    utterance.onend = () => {
      isPlaying.value = false
    }
    utterance.onerror = (e) => {
      if (e.error !== 'interrupted') {
        console.error('[VoicePlayback] 语音错误:', e.error)
      }
      isPlaying.value = false
    }

    synth.speak(utterance)
  }

  function stop() {
    synth.cancel()
    isPlaying.value = false
  }

  return { isPlaying, speak, stop }
}
