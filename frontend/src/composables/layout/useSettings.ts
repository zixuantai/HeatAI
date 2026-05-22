import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import Croppie from 'croppie'
import 'croppie/croppie.css'
import { setAudioVolume } from '@/composables/chat/useAudioPlayer'

export function useSettings(userId: () => string | undefined) {
  const settingsNavItems = [
    { key: 'voice' as const, label: '声音', icon: 'Headset' as const },
    { key: 'theme' as const, label: '主题', icon: 'Sunny' as const },
    { key: 'personalization' as const, label: '个性化', icon: 'MagicStick' as const }
  ]
  const personalizationItems = [
    { key: 'gentle', label: '温柔体贴', descWeaken: '更专业、事实性更强', descEnhance: '更友好、更亲近' },
    { key: 'enthusiastic', label: '热情洋溢', descWeaken: '更加冷静中立', descEnhance: '更加活力充沛' },
    { key: 'structure', label: '标题和列表', descWeaken: '更多段落文本，而非列表结构', descEnhance: '多用清晰格式和列表结构' },
    { key: 'emoji', label: '表情符号', descWeaken: '尽量少用表情符号', descEnhance: '使用更多表情符号' }
  ]

  const voiceEnabledKey = computed(() => `heatai_voice_enabled_${userId() || ''}`)
  const voiceTypeKey = computed(() => `heatai_voice_type_${userId() || ''}`)
  const voiceVolumeKey = computed(() => `heatai_voice_volume_${userId() || ''}`)
  const themeKey = computed(() => `heatai_theme_${userId() || ''}`)
  const personalizationKeyPrefix = computed(() => `heatai_personalization_${userId() || ''}_`)

  const activeSettingsNav = ref<string>('voice')

  const voiceEnabled = ref(localStorage.getItem(voiceEnabledKey.value) !== 'false')
  const voiceOptions = [
    { label: '阳光大男孩', value: 'longanyang' },
    { label: '欢脱元气女', value: 'longanhuan' },
    { label: '天真烂漫女童', value: 'longhuhu_v3' },
    { label: '阳光顽皮男', value: 'longjielidou_v3' }
  ]
  const voiceType = ref(localStorage.getItem(voiceTypeKey.value) || 'longanhuan')

  const savedVolume = localStorage.getItem(voiceVolumeKey.value)
  const voiceVolume = ref(savedVolume !== null ? Number(savedVolume) : 80)

  setAudioVolume(voiceVolume.value / 100)

  const themeMode = ref(localStorage.getItem(themeKey.value) || 'light')

  const personalizationValues = ref<Record<string, number>>({})

  const croppieRef = ref<HTMLElement | null>(null)
  const croppieVisible = ref(false)
  const cropDialogVisible = ref(false)
  const cropLoading = ref(false)
  const avatarPreview = ref<string | null>(null)
  let croppieInstance: Croppie | null = null

  function loadPersonalizationValues() {
    const values: Record<string, number> = {}
    for (const item of personalizationItems) {
      const key = personalizationKeyPrefix.value + item.key
      const stored = localStorage.getItem(key)
      values[item.key] = stored !== null ? Number(stored) : 0
    }
    personalizationValues.value = values
  }

  function handlePersonalizationChange(itemKey: string, val: number) {
    personalizationValues.value[itemKey] = val
    localStorage.setItem(personalizationKeyPrefix.value + itemKey, String(val))
  }

  function applyTheme(mode: string) {
    if (mode === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark')
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.removeAttribute('data-theme')
      document.documentElement.classList.remove('dark')
    }
  }

  function handleThemeChange(mode: string) {
    themeMode.value = mode
    localStorage.setItem(themeKey.value, mode)
    applyTheme(mode)
  }

  function handleVoiceEnabledChange(val: boolean) {
    localStorage.setItem(voiceEnabledKey.value, String(val))
  }

  function handleVoiceTypeChange(val: string) {
    console.log('[Settings] 音色切换:', val, 'key:', voiceTypeKey.value)
    localStorage.setItem(voiceTypeKey.value, val)
  }

  function handleVoiceVolumeChange(val: number) {
    voiceVolume.value = val
    localStorage.setItem(voiceVolumeKey.value, String(val))
    setAudioVolume(val / 100)
  }

  function onSettingsOpen() {
    activeSettingsNav.value = settingsNavItems[0]?.key || 'voice'
    loadPersonalizationValues()
    const savedTheme = localStorage.getItem(themeKey.value) || 'light'
    themeMode.value = savedTheme
    const savedVol = localStorage.getItem(voiceVolumeKey.value)
    voiceVolume.value = savedVol !== null ? Number(savedVol) : 80
    setAudioVolume(voiceVolume.value / 100)
    const savedVoiceType = localStorage.getItem(voiceTypeKey.value)
    console.log('[Settings] onSettingsOpen - voiceTypeKey:', voiceTypeKey.value, 'savedVoiceType:', savedVoiceType)
    if (savedVoiceType) {
      voiceType.value = savedVoiceType
    }
  }

  let pendingCropPhoto: string | null = null

  function handleAvatarFileChange(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      pendingCropPhoto = reader.result as string
      cropDialogVisible.value = true
    }
    reader.readAsDataURL(file)
    ;(e.target as HTMLInputElement).value = ''
  }

  function onCropDialogOpened() {
    if (!pendingCropPhoto) return
    const photo = pendingCropPhoto
    pendingCropPhoto = null
    setTimeout(() => {
      initCroppie(photo)
    }, 50)
  }

  function onCropDialogClosed() {
    destroyCroppie()
    pendingCropPhoto = null
  }

  function initCroppie(photo: string) {
    destroyCroppie()
    if (!croppieRef.value) return
    try {
      croppieInstance = new Croppie(croppieRef.value, {
        viewport: { width: 200, height: 200, type: 'circle' },
        boundary: { width: 300, height: 300 },
        enableOrientation: true,
        enforceBoundary: true,
        enableZoom: true,
        mouseWheelZoom: true,
        showZoomer: true,
      })
      croppieInstance.bind({ url: photo })
    } catch {
      // ignore
    }
  }

  function destroyCroppie() {
    try {
      croppieInstance?.destroy()
    } catch {
      // ignore
    }
    croppieInstance = null
    if (croppieRef.value) {
      croppieRef.value.innerHTML = ''
      croppieRef.value.classList.remove('croppie-container')
    }
  }

  function cancelCrop() {
    destroyCroppie()
    croppieVisible.value = false
    cropDialogVisible.value = false
  }

  async function confirmCrop() {
    if (!croppieInstance) return
    cropLoading.value = true
    try {
      const result = await croppieInstance.result({
        type: 'base64',
        size: 'viewport',
      })
      avatarPreview.value = result
      destroyCroppie()
      croppieVisible.value = false
      cropDialogVisible.value = false
    } catch {
      ElMessage.error('图片裁剪失败')
    } finally {
      cropLoading.value = false
    }
  }

  function resetCroppie() {
    destroyCroppie()
    croppieVisible.value = false
    cropDialogVisible.value = false
    pendingCropPhoto = null
  }

  return {
    settingsNavItems,
    personalizationItems,
    activeSettingsNav,
    voiceEnabled,
    voiceOptions,
    voiceType,
    voiceVolume,
    themeMode,
    personalizationValues,
    croppieRef,
    croppieVisible,
    cropDialogVisible,
    cropLoading,
    avatarPreview,
    loadPersonalizationValues,
    handlePersonalizationChange,
    applyTheme,
    handleThemeChange,
    handleVoiceEnabledChange,
    handleVoiceTypeChange,
    handleVoiceVolumeChange,
    onSettingsOpen,
    handleAvatarFileChange,
    onCropDialogOpened,
    onCropDialogClosed,
    cancelCrop,
    confirmCrop,
    resetCroppie,
    destroyCroppie,
    voiceEnabledKey,
    voiceTypeKey,
    voiceVolumeKey,
    themeKey
  }
}