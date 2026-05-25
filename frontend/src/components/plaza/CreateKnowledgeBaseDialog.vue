<template>
  <el-dialog
    v-model="visible"
    title="创建知识库"
    width="880px"
    :close-on-click-modal="false"
    :close-on-press-escape="!processing"
    :show-close="!processing"
    destroy-on-close
    class="create-kb-dialog"
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="create-kb-form">
      <el-form-item label="知识库头像">
        <div class="kb-avatar-picker">
          <div class="avatar-preview-area">
            <label class="avatar-upload-label">
              <input ref="avatarInputRef" type="file" accept="image/*" class="avatar-input-hidden" @change="handleAvatarChange" />
              <div class="avatar-preview-box" :class="{ 'has-custom': avatarPreview }">
                <img v-if="avatarPreview" :src="avatarPreview" alt="头像预览" class="avatar-preview-img" />
                <span
                  v-else-if="selectedDefaultAvatar"
                  class="avatar-default-preview"
                  :style="{ background: defaultAvatars[selectedDefaultAvatar]?.bg }"
                >{{ defaultAvatars[selectedDefaultAvatar]?.icon }}</span>
                <el-icon v-else :size="28"><Plus /></el-icon>
              </div>
            </label>
            <span class="avatar-hint">点击上传自定义头像，或从下方选择默认头像</span>
          </div>
          <div class="default-avatar-grid">
            <div
              v-for="(item, key) in defaultAvatars"
              :key="key"
              class="default-avatar-item"
              :class="{ active: selectedDefaultAvatar === key && !avatarPreview }"
              :style="{ background: item.bg }"
              @click="handleSelectDefaultAvatar(key)"
            >
              {{ item.icon }}
            </div>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="知识库名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入知识库名称" maxlength="50" show-word-limit />
      </el-form-item>

      <el-form-item label="知识库简介" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          placeholder="请输入知识库简介"
          :rows="3"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="上传文档">
        <div class="upload-area">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            multiple
            :limit="10"
            accept=".pdf,.doc,.docx,.txt,.md,.xlsx,.xls,.ppt,.pptx,.csv"
            class="kb-upload"
          >
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              选择文件
            </el-button>
            <template #tip>
              <div class="upload-tip">支持 PDF、Word、TXT、Markdown、Excel、PPT、CSV 格式，单个文件不超过 50MB</div>
            </template>
          </el-upload>
        </div>
      </el-form-item>

      <el-form-item label="快捷问题">
        <div class="quick-questions-editor">
          <div v-for="(q, index) in form.quick_questions" :key="index" class="quick-question-item">
            <el-input v-model="form.quick_questions[index]" placeholder="请输入快捷问题" maxlength="30" />
            <el-button text type="danger" @click="removeQuestion(index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div class="quick-question-actions">
            <el-button
              v-if="form.quick_questions.length < 4"
              type="primary"
              class="action-btn"
              @click="addQuestion"
            >
              <el-icon><Plus /></el-icon>
              添加问题
            </el-button>
            <el-button
              type="primary"
              class="action-btn"
              :loading="generatingQuestions"
              @click="handleGenerateQuestions"
            >
              <el-icon><MagicStick /></el-icon>
              AI 自动生成
            </el-button>
          </div>
          <div class="quick-question-hint">最多支持 4 个快捷问题</div>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false" :disabled="processing">取消</el-button>
      <el-button type="primary" :loading="processing" @click="handleSubmit">创建并发布</el-button>
    </template>

    <!-- 处理中遮罩 -->
    <div v-if="processing" class="processing-overlay">
      <div class="processing-dialog">
        <el-icon class="processing-icon is-loading" :size="48"><Loading /></el-icon>
        <h3 class="processing-title">正在处理中</h3>
        <p class="processing-desc">正在上传文档并进行智能解析，可能需要等待较长时间，请耐心等待...</p>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { Plus, Delete, MagicStick, Upload, Loading } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules, type UploadFile } from 'element-plus'
import { createKnowledgeBaseApi, uploadDocumentToKbApi, generateQuickQuestionsApi, previewQuickQuestionsApi } from '@/api/knowledgeBases'

const defaultAvatars: Record<string, { bg: string; icon: string }> = {
  heat:   { bg: 'linear-gradient(135deg, #ff6b35 0%, #f7c948 100%)', icon: '🔥' },
  green:  { bg: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)', icon: '🌿' },
  blue:   { bg: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', icon: '💧' },
  purple: { bg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', icon: '⚡' },
  pink:   { bg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', icon: '📚' },
  orange: { bg: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', icon: '🏭' },
  cyan:   { bg: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', icon: '📊' },
  dark:   { bg: 'linear-gradient(135deg, #434343 0%, #1a1a2e 100%)', icon: '⚙️' },
}

interface Props {
  modelValue: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'created'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const visible = ref(false)
const formRef = ref<FormInstance>()
const uploadRef = ref()
const processing = ref(false)
const generatingQuestions = ref(false)
const avatarPreview = ref<string | null>(null)
const selectedDefaultAvatar = ref<string>('')
const avatarInputRef = ref<HTMLInputElement>()
const selectedFiles = ref<File[]>([])

const form = reactive({
  name: '',
  description: '',
  avatar: '',
  cover_color: '',
  quick_questions: [] as string[]
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度为1-50位', trigger: 'blur' }
  ]
}

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('头像文件大小不能超过 2MB')
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    avatarPreview.value = e.target?.result as string
    form.avatar = avatarPreview.value
    selectedDefaultAvatar.value = ''
  }
  reader.readAsDataURL(file)
  input.value = ''
}

function handleSelectDefaultAvatar(key: string) {
  selectedDefaultAvatar.value = key
  form.avatar = defaultAvatars[key].bg
  avatarPreview.value = null
}

function handleFileChange(file: UploadFile) {
  if (file.raw) {
    selectedFiles.value.push(file.raw)
  }
}

function handleFileRemove(file: UploadFile) {
  const index = selectedFiles.value.findIndex(f => f.name === file.name)
  if (index > -1) {
    selectedFiles.value.splice(index, 1)
  }
}

function addQuestion() {
  if (form.quick_questions.length < 4) {
    form.quick_questions.push('')
  }
}

function removeQuestion(index: number) {
  form.quick_questions.splice(index, 1)
}

async function handleGenerateQuestions() {
  if (!form.name.trim()) {
    ElMessage.warning('请先填写知识库名称')
    return
  }

  generatingQuestions.value = true
  try {
    const result = await previewQuickQuestionsApi(form.name.trim(), form.description?.trim() || '')
    if (result.data && result.data.length > 0) {
      form.quick_questions = result.data.slice(0, 4)
      ElMessage.success('快捷问题生成成功')
    } else {
      ElMessage.info('未能生成快捷问题，请手动添加')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '生成快捷问题失败')
  } finally {
    generatingQuestions.value = false
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  processing.value = true
  try {
    const kb = await createKnowledgeBaseApi({
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      avatar: form.avatar || undefined,
      cover_color: form.cover_color || undefined,
      quick_questions: form.quick_questions.filter(q => q.trim()).slice(0, 4)
    })

    if (selectedFiles.value.length > 0) {
      for (const file of selectedFiles.value) {
        try {
          await uploadDocumentToKbApi(kb.id, file)
        } catch (error: any) {
          ElMessage.warning(`文档 ${file.name} 上传失败: ${error.message}`)
        }
      }
    }

    ElMessage.success('知识库创建成功')
    visible.value = false
    emit('created')
  } catch (error: any) {
    ElMessage.error(error.message || '创建失败')
  } finally {
    processing.value = false
  }
}

function handleClosed() {
  form.name = ''
  form.description = ''
  form.avatar = ''
  form.cover_color = ''
  form.quick_questions = []
  avatarPreview.value = null
  selectedDefaultAvatar.value = ''
  selectedFiles.value = []
}
</script>

<style scoped>
.create-kb-form {
  padding: 10px 0;
}

.create-kb-dialog :deep(.el-dialog__body) {
  position: relative;
}

.kb-avatar-picker {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.avatar-preview-area {
  display: flex;
  align-items: center;
  gap: 14px;
}

.avatar-upload-label {
  cursor: pointer;
  flex-shrink: 0;
}

.avatar-input-hidden {
  display: none;
}

.avatar-preview-box {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  border: 2px dashed var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);
  overflow: hidden;
  background: var(--color-bg);
}

.avatar-preview-box:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.avatar-preview-box.has-custom {
  border-style: solid;
  border-color: var(--color-primary);
}

.avatar-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-default-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.avatar-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.default-avatar-grid {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.default-avatar-item {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  border: 3px solid transparent;
  transition: all var(--transition-fast);
  flex-shrink: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.default-avatar-item:hover {
  transform: scale(1.12);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.default-avatar-item.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.3);
  transform: scale(1.12);
}

.upload-area {
  width: 100%;
}

.kb-upload {
  width: 100%;
}

.upload-tip {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 4px;
}

.kb-upload :deep(.el-upload) {
  width: 100%;
  display: flex;
  justify-content: flex-start;
}

.kb-upload :deep(.el-upload__text) {
  color: #fff !important;
}

.action-btn,
.action-btn:hover,
.action-btn:focus {
  color: #fff !important;
}

.quick-questions-editor {
  width: 100%;
}

.quick-question-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.quick-question-item .el-input {
  flex: 1;
}

.quick-question-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.quick-question-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 4px;
}

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
}

.processing-dialog {
  text-align: center;
  padding: 48px 40px;
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  max-width: 400px;
}

.processing-icon {
  color: var(--color-primary);
  animation: rotating 1.2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.processing-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  margin: 20px 0 12px;
}

.processing-desc {
  font-size: 14px;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin: 0;
}
</style>
