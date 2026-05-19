<template>
  <div class="source-panel">
    <div class="source-panel-header">
      <h3 class="source-panel-title">知识来源</h3>
      <button class="source-panel-close" @click="close">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <div class="source-panel-body">
      <div v-if="sources.length === 0" class="source-empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.4">
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
        <p>暂无相关知识来源</p>
      </div>

      <div v-else class="source-list">
        <div
          v-for="(source, index) in sources"
          :key="index"
          class="source-card"
          :class="{ expanded: expandedIndex === index }"
        >
          <div class="source-card-inner" @click="toggleExpand(index, source.title)">
            <div class="source-card-top">
              <div class="source-type-badge" :style="{ '--badge-color': getFileTypeColor(docInfoCache[index]?.file_type || '') }">
                <span class="source-type-ext">{{ (docInfoCache[index]?.file_type || '文档').toUpperCase() }}</span>
              </div>
              <div class="source-meta-row">
                <span class="source-led" :class="{
                  'source-led-online': docInfoCache[index]?.status === 'completed',
                  'source-led-warning': docInfoCache[index] && docInfoCache[index]!.status !== 'completed'
                }" />
                <span class="source-meta-label">{{ source.label }}</span>
              </div>
            </div>

            <h3 class="source-card-name" :title="source.title">{{ source.title }}</h3>

            <div class="source-card-info">
              <div class="source-info-item" v-if="docInfoCache[index]">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="6" x2="12" y2="12"/><polyline points="16 14 12 12 8 14"/></svg>
                <span>{{ formatFileSize(docInfoCache[index]?.file_size || 0) }}</span>
              </div>
              <div class="source-info-item" v-if="docInfoCache[index]">
                <span class="source-info-chip">{{ docInfoCache[index]?.chunk_count || 0 }} 块</span>
              </div>
              <div class="source-info-item source-info-loading" v-if="!docInfoCache[index] && !loadErrors[index] && loadingIndex !== index">
                <span>点击查看详情</span>
              </div>
            </div>
          </div>

          <div v-if="expandedIndex === index" class="source-card-detail">
            <div v-if="loadingIndex === index" class="source-loading">
              <span class="source-loading-spinner"></span>
              <span class="source-loading-text">加载文档分块...</span>
            </div>
            <div v-else-if="loadErrors[index]" class="source-error">
              <p>{{ loadErrors[index] }}</p>
            </div>
            <div v-else-if="chunkData[index]" class="source-chunks">
              <div class="source-chunks-header">
                <span class="source-chunks-count">共 {{ chunkData[index]!.chunks.length }} 个分块</span>
              </div>
              <div
                v-for="chunk in chunkData[index]!.chunks"
                :key="chunk.id"
                class="source-chunk-item"
              >
                <div class="source-chunk-index">
                  <span class="source-chunk-tag">#{{ chunk.chunk_index + 1 }}</span>
                  <span class="source-chunk-title">{{ chunk.title }}</span>
                </div>
                <div class="source-chunk-content">{{ chunk.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { getDocumentsApi } from '@/api/documents'
import { getDocumentChunksApi } from '@/api/documents'
import type { SourceItem } from '@/composables/chat/useSourceExtractor'
import type { ChunkInfo, DocumentInfo } from '@/types'

const props = defineProps<{
  sources: SourceItem[]
}>()

const emit = defineEmits<{
  close: []
}>()

const expandedIndex = ref<number | null>(null)
const loadingIndex = ref<number | null>(null)
const chunkData = ref<Record<number, { chunks: ChunkInfo[] } | null>>({})
const loadErrors = ref<Record<number, string>>({})
const docInfoCache = reactive<Record<number, DocumentInfo | null>>({})

function close() {
  emit('close')
}

async function toggleExpand(index: number, title: string) {
  if (expandedIndex.value === index) {
    expandedIndex.value = null
    return
  }

  expandedIndex.value = index

  if (chunkData.value[index] !== undefined || loadErrors.value[index] !== undefined) {
    return
  }

  loadingIndex.value = index
  try {
    const result = await getDocumentsApi(200, 0, title)
    const matched = result.items.find(
      item => item.original_filename === title ||
        item.filename === title ||
        item.original_filename.includes(title) ||
        title.includes(item.original_filename)
    )

    if (!matched) {
      loadErrors.value[index] = '未找到匹配的文档'
      return
    }

    docInfoCache[index] = matched

    const chunksResult = await getDocumentChunksApi(matched.id)
    chunkData.value[index] = {
      chunks: chunksResult.chunks
    }
  } catch {
    loadErrors.value[index] = '加载文档分块失败'
  } finally {
    loadingIndex.value = null
  }
}

function getFileTypeColor(fileType: string): string {
  const map: Record<string, string> = {
    pdf: '#e74c3c',
    docx: '#2b579a',
    doc: '#2b579a',
    html: '#e67e22',
    htm: '#e67e22',
    txt: '#7f8c8d',
  }
  return map[fileType.toLowerCase()] || '#94a3b8'
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}
</script>

<style scoped>
.source-panel {
  width: 420px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  flex-shrink: 0;
  overflow: hidden;
}

.source-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.source-panel-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin: 0;
}

.source-panel-close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  padding: 0;
}

.source-panel-close:hover {
  background: var(--color-bg);
  color: var(--color-text-main);
}

.source-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.source-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 12px;
}

.source-empty svg {
  color: var(--color-text-muted);
}

.source-empty p {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  margin: 0;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Document Card (matching knowledge base style) ── */
.source-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.source-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.source-card.expanded {
  border-color: var(--color-primary);
  box-shadow: 0 4px 20px rgba(79, 70, 229, 0.12);
}

.source-card-inner {
  padding: 20px 18px;
  cursor: pointer;
  position: relative;
  transition: background var(--transition-fast);
}

.source-card-inner:hover {
  background: rgba(79, 70, 229, 0.02);
}

.source-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.source-type-badge {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--badge-color, #4F46E5) 15%, white),
    color-mix(in srgb, var(--badge-color, #4F46E5) 8%, white)
  );
  border: 1.5px solid color-mix(in srgb, var(--badge-color, #4F46E5) 25%, transparent);
}

.source-type-ext {
  font-family: var(--font-family);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--badge-color, #4F46E5);
}

.source-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-led {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
  flex-shrink: 0;
}

.source-led-online {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

.source-led-warning {
  background: #f59e0b;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);
}

.source-meta-label {
  font-family: var(--font-family);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

.source-card-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-main);
  margin: 0 0 14px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.source-card-info {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.source-info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.source-info-chip {
  font-family: var(--font-family);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-primary);
  background: rgba(79, 70, 229, 0.06);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.source-info-loading {
  color: var(--color-text-subtle);
  font-size: var(--font-size-sm);
}

/* ── Expanded Detail ────────────────────────────────── */
.source-card-detail {
  border-top: 1px solid var(--color-border-light);
  padding: 16px 18px;
}

.source-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 0;
}

.source-loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.source-loading-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.source-error {
  padding: 8px 0;
}

.source-error p {
  font-size: var(--font-size-sm);
  color: #ef4444;
  margin: 0;
}

.source-chunks-header {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-light);
}

.source-chunks-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
}

.source-chunks {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-chunk-item {
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  background: var(--color-bg);
  overflow: hidden;
}

.source-chunk-index {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-surface);
}

.source-chunk-tag {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-muted);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.source-chunk-title {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-chunk-content {
  font-size: var(--font-size-sm);
  color: var(--color-text-main);
  line-height: var(--leading-relaxed);
  padding: 10px 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>