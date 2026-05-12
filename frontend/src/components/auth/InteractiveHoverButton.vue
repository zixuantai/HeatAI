<template>
  <button
    class="hover-btn"
    :class="[variantClass, { 'is-loading': loading }]"
    :disabled="disabled || loading"
    v-bind="$attrs"
  >
    <span class="hover-btn-text">
      <slot>{{ text }}</slot>
    </span>
    <div class="hover-btn-overlay">
      <span><slot>{{ text }}</slot></span>
      <svg
        v-if="!icon"
        class="hover-btn-arrow"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <line x1="5" y1="12" x2="19" y2="12" />
        <polyline points="12 5 19 12 12 19" />
      </svg>
      <slot v-else name="icon">
        <component :is="icon" class="hover-btn-arrow" />
      </slot>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  text?: string
  variant?: 'primary' | 'outline'
  loading?: boolean
  disabled?: boolean
  icon?: any
}>(), {
  text: 'Button',
  variant: 'primary',
  loading: false,
  disabled: false,
})

defineOptions({ inheritAttrs: false })

const variantClass = computed(() => `hover-btn--${props.variant}`)
</script>

<style scoped>
.hover-btn {
  position: relative;
  cursor: pointer;
  overflow: hidden;
  border-radius: 9999px;
  border: none;
  padding: 0;
  text-align: center;
  font-weight: 600;
  font-size: 15px;
  height: 48px;
  width: 100%;
  font-family: inherit;
  background: #1e293b;
  color: #fff;
  transition: all 0.2s ease;
  letter-spacing: 0.3px;
}

.hover-btn--outline {
  background: #fff;
  color: #1e293b;
  border: 1px solid #e2e8f0;
}

.hover-btn:disabled,
.hover-btn.is-loading {
  cursor: not-allowed;
  opacity: 0.7;
}

.hover-btn-text {
  display: inline-block;
  transition: all 0.3s ease;
}

.hover-btn:hover:not(:disabled):not(.is-loading) .hover-btn-text {
  transform: translateX(40px);
  opacity: 0;
}

.hover-btn-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  opacity: 0;
  transition: all 0.3s ease;
  border-radius: 9999px;
}

.hover-btn--outline .hover-btn-overlay {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}

.hover-btn:hover:not(:disabled):not(.is-loading) .hover-btn-overlay {
  opacity: 1;
}

.hover-btn-arrow {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.hover-btn:active:not(:disabled):not(.is-loading) {
  transform: scale(0.97);
}
</style>