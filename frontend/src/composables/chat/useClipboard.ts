import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useClipboard() {
  const copied = ref(false)

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      copied.value = true
      ElMessage.success('已复制到剪贴板')
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      try {
        document.execCommand('copy')
        copied.value = true
        ElMessage.success('已复制到剪贴板')
      } catch {
        ElMessage.error('复制失败')
      }
      document.body.removeChild(textarea)
    } finally {
      setTimeout(() => {
        copied.value = false
      }, 2000)
    }
  }

  return { copied, copyText }
}
