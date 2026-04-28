<template>
  <div class="mascot-wrapper" ref="mascotRef">
    <div class="mascot">
      <div class="mascot-body">
        <div class="mascot-face">
          <div class="eye-group">
            <div class="eye">
              <div class="pupil" :style="pupilStyle" v-if="!isPassword"></div>
              <svg v-else class="closed-eye" viewBox="0 0 28 30">
                <path d="M5 16 Q14 10 23 16" stroke="#2d1b0e" stroke-width="2.8" fill="none" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="eye">
              <div class="pupil" :style="pupilStyle" v-if="!isPassword"></div>
              <svg v-else class="closed-eye" viewBox="0 0 28 30">
                <path d="M5 16 Q14 10 23 16" stroke="#2d1b0e" stroke-width="2.8" fill="none" stroke-linecap="round"/>
              </svg>
            </div>
          </div>
          <div class="mouth" :class="{ surprised: isFocused, shut: isPassword }">
            <div class="tongue" v-if="isFocused && !isPassword"></div>
          </div>
          <div class="blush blush-left"></div>
          <div class="blush blush-right"></div>
        </div>
      </div>
      <div class="flame-particles">
        <span class="flame-particle" v-for="i in 8" :key="i" :style="flameStyle(i)"></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  isFocused?: boolean
  isPassword?: boolean
}>()

const mascotRef = ref<HTMLElement | null>(null)
const pupilX = ref(0)
const pupilY = ref(0)

const pupilStyle = computed(() => ({
  transform: `translate(calc(-50% + ${pupilX.value}px), calc(-50% + ${pupilY.value}px))`
}))

function handleMouseMove(e: MouseEvent) {
  if (!mascotRef.value) return
  const rect = mascotRef.value.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2

  const nx = (e.clientX - cx) / (rect.width * 2.5)
  const ny = (e.clientY - cy) / (rect.height * 2.5)

  const clampedX = Math.max(-1, Math.min(1, nx))
  const clampedY = Math.max(-1, Math.min(1, ny))

  const maxMove = 8
  pupilX.value = clampedX * maxMove
  pupilY.value = clampedY * maxMove
}

function flameStyle(i: number) {
  const delay = (i - 1) * 0.15
  const xOffset = Math.sin(i * 1.2) * 8
  const yOffset = -8 - Math.abs(Math.cos(i * 0.8)) * 4
  const size = 6 + (i % 3) * 2
  return {
    '--delay': `${delay}s`,
    '--x': `${xOffset}px`,
    '--y': `${yOffset}px`,
    '--size': `${size}px`,
    animationDelay: `${delay}s`
  }
}

onMounted(() => {
  document.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', handleMouseMove)
})
</script>

<style scoped>
.mascot-wrapper {
  position: relative;
  width: 150px;
  height: 150px;
  margin: 0 auto 4px;
}

.mascot {
  position: relative;
  width: 100%;
  height: 100%;
  animation: mascot-float 3.5s ease-in-out infinite;
}

.mascot-body {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(170deg, #ffa94d 0%, #ff7b39 35%, #f06020 100%);
  position: relative;
  box-shadow:
    0 10px 36px rgba(255, 80, 30, 0.32),
    inset 0 -10px 20px rgba(0, 0, 0, 0.08),
    inset 0 10px 18px rgba(255, 255, 255, 0.12);
}

.mascot-face {
  position: absolute;
  top: 52%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 96px;
  height: 72px;
}

.eye-group {
  display: flex;
  justify-content: center;
  gap: 22px;
}

.eye {
  width: 28px;
  height: 30px;
  background: #fff;
  border-radius: 50%;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 2px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.pupil {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 13px;
  height: 15px;
  background: radial-gradient(circle at 40% 35%, #3a2210, #1a0d04);
  border-radius: 50%;
  transition: transform 0.12s ease-out;
}

.pupil::after {
  content: '';
  position: absolute;
  top: 3px;
  right: 3px;
  width: 5px;
  height: 5px;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 50%;
}

.closed-eye {
  width: 28px;
  height: 30px;
}

.closed-eye path {
  animation: eye-blink-in 0.18s ease-out;
}

.mouth {
  width: 16px;
  height: 9px;
  background: #2d1b0e;
  border-radius: 0 0 50% 50%;
  margin: 10px auto 0;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
}

.mouth.surprised {
  width: 22px;
  height: 20px;
  border-radius: 50%;
  margin-top: 7px;
}

.mouth.shut {
  width: 22px;
  height: 6px;
  border-radius: 50%;
  margin-top: 11px;
  background: transparent;
  border-bottom: 3px solid #2d1b0e;
}

.tongue {
  position: absolute;
  bottom: 3px;
  left: 50%;
  transform: translateX(-50%);
  width: 9px;
  height: 6px;
  background: #ff6b6b;
  border-radius: 0 0 50% 50%;
}

.blush {
  position: absolute;
  width: 14px;
  height: 7px;
  background: rgba(255, 90, 90, 0.32);
  border-radius: 50%;
  top: 30px;
}

.blush-left {
  left: -2px;
}

.blush-right {
  right: -2px;
}

.flame-particles {
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 44px;
  height: 32px;
}

.flame-particle {
  position: absolute;
  width: var(--size, 6px);
  height: var(--size, 6px);
  background: #ffb347;
  border-radius: 50% 50% 50% 0;
  transform: translate(var(--x, 0), var(--y, 0)) rotate(-45deg) scale(0);
  left: calc(50% - var(--size, 6px) / 2);
  bottom: 0;
  opacity: 0;
  animation: flame-particle 1.3s var(--delay, 0s) ease-out infinite;
}

@keyframes mascot-float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  30% { transform: translateY(-7px) rotate(2deg); }
  60% { transform: translateY(-2px) rotate(0deg); }
  80% { transform: translateY(-5px) rotate(-1.5deg); }
}

@keyframes flame-particle {
  0% {
    transform: translate(var(--x, 0), var(--y, 0)) rotate(-45deg) scale(0.15);
    opacity: 1;
  }
  35% {
    transform: translate(var(--x, 0), calc(var(--y, 0) - 12px)) rotate(-45deg) scale(1);
    opacity: 0.75;
  }
  100% {
    transform: translate(var(--x, 0), calc(var(--y, 0) - 28px)) rotate(-45deg) scale(0);
    opacity: 0;
  }
}

@keyframes eye-blink-in {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
</style>
