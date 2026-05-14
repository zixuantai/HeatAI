import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

export function useImageUpload(maxCount: number = 5, maxSizeMB: number = 10) {
  const uploadedImages = ref<string[]>([])

  function processImageFiles(files: FileList | File[], onDone?: () => void) {
    const remaining = maxCount - uploadedImages.value.length
    if (remaining <= 0) {
      ElMessage.warning(`最多只能上传 ${maxCount} 张图片`)
      return
    }

    const filesToProcess = Math.min(files.length, remaining)
    let loaded = 0
    let skipped = 0

    const onAllDone = () => {
      if (onDone) {
        nextTick(() => onDone())
      }
    }

    for (let i = 0; i < filesToProcess; i++) {
      const file = files[i]
      if (!file.type.startsWith('image/')) {
        skipped++
        if (loaded + skipped === filesToProcess) onAllDone()
        continue
      }

      if (file.size > maxSizeMB * 1024 * 1024) {
        ElMessage.warning(`图片 "${file.name}" 超过 ${maxSizeMB}MB，已跳过`)
        skipped++
        if (loaded + skipped === filesToProcess) onAllDone()
        continue
      }

      const reader = new FileReader()
      reader.onload = (e) => {
        const base64 = e.target?.result as string
        if (base64) {
          uploadedImages.value.push(base64)
        }
        loaded++
        if (loaded + skipped === filesToProcess) {
          onAllDone()
        }
      }
      reader.readAsDataURL(file)
    }

    if (files.length > filesToProcess) {
      ElMessage.warning(`最多上传 ${maxCount} 张，已自动选取前 ${filesToProcess} 张`)
    }
  }

  function handleImageSelect(event: Event, onDone?: () => void) {
    const input = event.target as HTMLInputElement
    const files = input.files
    if (!files || files.length === 0) return

    processImageFiles(files, () => {
      input.value = ''
      if (onDone) onDone()
    })
  }

  function handlePaste(event: ClipboardEvent, onDone?: () => void) {
    const items = event.clipboardData?.items
    if (!items) return

    const remaining = maxCount - uploadedImages.value.length
    if (remaining <= 0) {
      ElMessage.warning(`最多只能上传 ${maxCount} 张图片`)
      return
    }

    const imageItems: DataTransferItem[] = []
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      if (item.type.startsWith('image/')) {
        imageItems.push(item)
      }
    }

    if (imageItems.length === 0) return
    event.preventDefault()

    const toProcess = Math.min(imageItems.length, remaining)
    let loaded = 0
    let skipped = 0

    const onAllDone = () => {
      if (onDone) nextTick(() => onDone())
    }

    for (let i = 0; i < toProcess; i++) {
      const file = imageItems[i].getAsFile()
      if (!file) {
        skipped++
        if (loaded + skipped === toProcess) onAllDone()
        continue
      }

      if (file.size > maxSizeMB * 1024 * 1024) {
        ElMessage.warning('图片超过 10MB，已跳过')
        skipped++
        if (loaded + skipped === toProcess) onAllDone()
        continue
      }

      const reader = new FileReader()
      reader.onload = (e) => {
        const base64 = e.target?.result as string
        if (base64) {
          uploadedImages.value.push(base64)
        }
        loaded++
        if (loaded + skipped === toProcess) {
          onAllDone()
        }
      }
      reader.readAsDataURL(file)
    }

    if (imageItems.length > toProcess) {
      ElMessage.warning(`最多上传 ${maxCount} 张，已自动选取前 ${toProcess} 张`)
    }
  }

  function removeImage(index: number, onDone?: () => void) {
    uploadedImages.value.splice(index, 1)
    if (onDone) onDone()
  }

  return {
    uploadedImages,
    handleImageSelect,
    handlePaste,
    removeImage
  }
}