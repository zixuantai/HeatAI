<template>
  <div class="bottom-cards-row">
    <!-- 左侧：AI解答次数统计卡片 -->
    <div class="bottom-card stats-card clickable-card" @click="showStatsDialog = true">
      <p class="stats-line-1">截止 {{ todayDate }}，AI已为你解答了</p>
      <div class="stats-line-2">
        <!-- 左翼 -->
        <svg class="wing wing-left" width="44" height="40" viewBox="0 0 44 40" fill="none">
          <ellipse cx="22" cy="8" rx="16" ry="4" transform="rotate(28 22 8)" fill="#8b5cf6" opacity="0.8"/>
          <ellipse cx="24" cy="16" rx="15" ry="3.5" transform="rotate(10 24 16)" fill="#a78bfa" opacity="0.7"/>
          <ellipse cx="26" cy="24" rx="13" ry="3" transform="rotate(-8 26 24)" fill="#c4b5fd" opacity="0.6"/>
          <ellipse cx="28" cy="32" rx="10" ry="2.5" transform="rotate(-25 28 32)" fill="#ddd6fe" opacity="0.5"/>
        </svg>

        <span class="stats-count">{{ stats.ai_answer_count }} 次</span>

        <!-- 右翼 -->
        <svg class="wing wing-right" width="44" height="40" viewBox="0 0 44 40" fill="none">
          <ellipse cx="22" cy="8" rx="16" ry="4" transform="rotate(-28 22 8)" fill="#8b5cf6" opacity="0.8"/>
          <ellipse cx="20" cy="16" rx="15" ry="3.5" transform="rotate(-10 20 16)" fill="#a78bfa" opacity="0.7"/>
          <ellipse cx="18" cy="24" rx="13" ry="3" transform="rotate(8 18 24)" fill="#c4b5fd" opacity="0.6"/>
          <ellipse cx="16" cy="32" rx="10" ry="2.5" transform="rotate(25 16 32)" fill="#ddd6fe" opacity="0.5"/>
        </svg>
      </div>
      <p class="stats-line-3">
        超过了<span class="stats-percent">{{ stats.exceed_percentage }}%</span>的智慧供热客服用户
      </p>
    </div>

    <!-- AI解答次数详情弹窗 -->
    <el-dialog
      v-model="showStatsDialog"
      title="AI解答次数详情"
      width="480px"
      :close-on-click-modal="true"
      destroy-on-close
    >
      <div class="stats-dialog-placeholder">
        <p>详细信息待后续迭代升级</p>
      </div>
    </el-dialog>

    <!-- 右侧导航卡片 - 新对话页面 -->
    <div
      v-if="variant === 'chat'"
      class="bottom-card nav-card clickable-card"
      @click="$router.push('/plaza')"
    >
      <div class="nav-card-cover">
        <el-icon :size="28"><Promotion /></el-icon>
      </div>
      <div class="nav-card-body">
        <span class="nav-card-title">知识库广场</span>
        <span class="nav-card-subtitle">探索知识库广场，尝试更多知识库</span>
      </div>
    </div>

    <!-- 右侧导航卡片 - 知识库对话页面 -->
    <div
      v-if="variant === 'kbChat'"
      class="bottom-card nav-card clickable-card"
      @click="$router.push('/documents')"
    >
      <div class="nav-card-cover">
        <el-icon :size="28"><FolderOpened /></el-icon>
      </div>
      <div class="nav-card-body">
        <span class="nav-card-title">组织知识库</span>
        <span class="nav-card-subtitle">更适合你的知识库</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Promotion, FolderOpened } from '@element-plus/icons-vue'

defineProps<{
  variant: 'chat' | 'kbChat'
}>()

const showStatsDialog = ref(false)

const stats = { ai_answer_count: 0, exceed_percentage: 0 }

const todayDate = computed(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
})
</script>

<style scoped>
.bottom-cards-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 48px;
  width: 100%;
  max-width: 900px;
}

.bottom-card {
  flex: 1;
  min-width: 0;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--neu-card);
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 42px 20px;
  position: relative;
  overflow: hidden;
}

/* ── 卡片 hover 动态光效 ── */
.bottom-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0;
  background: linear-gradient(
    135deg,
    rgba(79, 70, 229, 0.04) 0%,
    rgba(99, 102, 241, 0.08) 50%,
    rgba(79, 70, 229, 0.04) 100%
  );
  transition: opacity 0.4s ease;
  pointer-events: none;
  z-index: 0;
}

.bottom-card:hover::before {
  opacity: 1;
}

.bottom-card:hover {
  transform: translateY(-4px);
  border-color: rgba(79, 70, 229, 0.3);
  box-shadow:
    0 12px 32px rgba(79, 70, 229, 0.12),
    8px 8px 20px var(--neu-shadow-dark),
    -8px -8px 20px var(--neu-shadow-light);
}

/* ── 可点击卡片特殊效果 ── */
.clickable-card {
  cursor: pointer;
}

.clickable-card:hover .nav-card-cover {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.25);
}

.clickable-card:hover .nav-card-title {
  color: var(--color-primary);
}

.clickable-card:active {
  transform: scale(0.97);
}

/* ── 统计卡片 hover ── */
.stats-card:hover .stats-count {
  filter: brightness(1.1);
}

/* ── 统计卡片内容 ── */
.stats-card > * {
  position: relative;
  z-index: 1;
}

.stats-line-1 {
  font-size: var(--font-size-sm);
  color: var(--color-text-subtle);
  margin: 0 0 16px;
  text-align: center;
  font-weight: var(--font-weight-medium);
}

.stats-line-2 {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.wing {
  flex-shrink: 0;
  transition: transform 0.4s ease, opacity 0.4s ease;
}

.stats-card:hover .wing-left {
  transform: translateX(-3px);
}

.stats-card:hover .wing-right {
  transform: translateX(3px);
}

.stats-count {
  font-size: 32px;
  font-weight: var(--font-weight-extrabold);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  transition: filter 0.4s ease;
}

.stats-line-3 {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0;
  text-align: center;
}

.stats-percent {
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

/* ── 导航卡片 ── */
.nav-card {
  flex-direction: row;
  justify-content: center;
  gap: 18px;
}

.nav-card > * {
  position: relative;
  z-index: 1;
}

.nav-card-cover {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-md);
  background: var(--gradient-subtle);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 0.4s ease;
}

.nav-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-card-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  line-height: 1.3;
  transition: color 0.3s ease;
}

.nav-card-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  line-height: 1.4;
}

@media (max-width: 640px) {
  .bottom-cards-row {
    flex-direction: column;
    gap: 12px;
  }

  .nav-card {
    flex-direction: row;
    justify-content: center;
    gap: 14px;
  }
}

.stats-dialog-placeholder {
  text-align: center;
  padding: 40px 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}
</style>