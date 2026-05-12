<template>
  <div class="chars-wrapper" :style="{ width: '550px', height: '400px' }">
    <!-- Purple tall rectangle - Back layer -->
    <div ref="purpleRef" class="char-obj" :style="purpleStyle">
      <div class="eye-row" :style="purpleEyes">
        <div ref="purpleEye1" class="eyeball" :style="purpleEye1Style">
          <div v-if="!isPurpleBlinking" class="pupil" :style="purplePupil1Style" />
        </div>
        <div ref="purpleEye2" class="eyeball" :style="purpleEye2Style">
          <div v-if="!isPurpleBlinking" class="pupil" :style="purplePupil2Style" />
        </div>
      </div>
    </div>

    <!-- Black tall rectangle - Middle layer -->
    <div ref="blackRef" class="char-obj" :style="blackStyle">
      <div class="eye-row" :style="blackEyes">
        <div ref="blackEye1" class="eyeball" :style="blackEye1Style">
          <div v-if="!isBlackBlinking" class="pupil" :style="blackPupil1Style" />
        </div>
        <div ref="blackEye2" class="eyeball" :style="blackEye2Style">
          <div v-if="!isBlackBlinking" class="pupil" :style="blackPupil2Style" />
        </div>
      </div>
    </div>

    <!-- Orange semi-circle - Front left -->
    <div ref="orangeRef" class="char-obj" :style="orangeStyle">
      <div class="eye-row" :style="orangeEyes">
        <div ref="orangePupil1" class="pupil-dot" :style="orangePupil1Style" />
        <div ref="orangePupil2" class="pupil-dot" :style="orangePupil2Style" />
      </div>
    </div>

    <!-- Yellow rounded rectangle - Front right -->
    <div ref="yellowRef" class="char-obj" :style="yellowStyle">
      <div class="eye-row" :style="yellowEyes">
        <div ref="yellowPupil1" class="pupil-dot" :style="yellowPupil1Style" />
        <div ref="yellowPupil2" class="pupil-dot" :style="yellowPupil2Style" />
      </div>
      <div class="mouth" :style="yellowMouth" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  isTyping?: boolean
  showPassword?: boolean
  passwordLength?: number
}>(), {
  isTyping: false,
  showPassword: false,
  passwordLength: 0,
})

// ---- Mouse tracking ----
const mx = ref(0)
const my = ref(0)
function onMouse(e: MouseEvent) { mx.value = e.clientX; my.value = e.clientY }

// ---- Template refs ----
const purpleRef = ref<HTMLElement>()
const blackRef = ref<HTMLElement>()
const orangeRef = ref<HTMLElement>()
const yellowRef = ref<HTMLElement>()
const purpleEye1 = ref<HTMLElement>()
const purpleEye2 = ref<HTMLElement>()
const blackEye1 = ref<HTMLElement>()
const blackEye2 = ref<HTMLElement>()
const orangePupil1 = ref<HTMLElement>()
const orangePupil2 = ref<HTMLElement>()
const yellowPupil1 = ref<HTMLElement>()
const yellowPupil2 = ref<HTMLElement>()

// ---- Blinking state ----
const isPurpleBlinking = ref(false)
const isBlackBlinking = ref(false)
const isLookingAtEachOther = ref(false)
const isPurplePeeking = ref(false)

let purpleBlinkTimer: ReturnType<typeof setTimeout> | null = null
let blackBlinkTimer: ReturnType<typeof setTimeout> | null = null
let peekTimer: ReturnType<typeof setTimeout> | null = null

// ---- Helpers ----
function calcSkew(el: HTMLElement | undefined): number {
  if (!el) return 0
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const d = mx.value - cx
  return Math.max(-6, Math.min(6, -d / 120))
}

function calcFace(el: HTMLElement | undefined, scaleX = 20, scaleY = 30) {
  if (!el) return { x: 0, y: 0 }
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 3
  return {
    x: Math.max(-15, Math.min(15, (mx.value - cx) / scaleX)),
    y: Math.max(-10, Math.min(10, (my.value - cy) / scaleY)),
  }
}

function pupilOffset(el: HTMLElement | undefined, maxDist: number, fx?: number, fy?: number) {
  if (fx !== undefined && fy !== undefined) return { x: fx, y: fy }
  if (!el) return { x: 0, y: 0 }
  const rect = el.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = mx.value - cx
  const dy = my.value - cy
  const dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxDist)
  const angle = Math.atan2(dy, dx)
  return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
}

// ---- Blink schedulers ----
function schedulePurpleBlink() {
  purpleBlinkTimer = setTimeout(() => {
    isPurpleBlinking.value = true
    setTimeout(() => { isPurpleBlinking.value = false; schedulePurpleBlink() }, 150)
  }, Math.random() * 4000 + 3000)
}
function scheduleBlackBlink() {
  blackBlinkTimer = setTimeout(() => {
    isBlackBlinking.value = true
    setTimeout(() => { isBlackBlinking.value = false; scheduleBlackBlink() }, 150)
  }, Math.random() * 4000 + 3000)
}
function schedulePeek() {
  peekTimer = setTimeout(() => {
    isPurplePeeking.value = true
    setTimeout(() => { isPurplePeeking.value = false; schedulePeek() }, 800)
  }, Math.random() * 3000 + 2000)
}

// ---- Watchers ----
watch(() => props.isTyping, (v) => {
  if (v) { isLookingAtEachOther.value = true; setTimeout(() => (isLookingAtEachOther.value = false), 800) }
  else isLookingAtEachOther.value = false
})

watch([() => props.passwordLength, () => props.showPassword], ([len, show]) => {
  if (len > 0 && show) schedulePeek()
  else { isPurplePeeking.value = false; if (peekTimer) { clearTimeout(peekTimer); peekTimer = null } }
})

onMounted(() => { window.addEventListener('mousemove', onMouse); schedulePurpleBlink(); scheduleBlackBlink() })
onUnmounted(() => {
  window.removeEventListener('mousemove', onMouse)
  if (purpleBlinkTimer) clearTimeout(purpleBlinkTimer)
  if (blackBlinkTimer) clearTimeout(blackBlinkTimer)
  if (peekTimer) clearTimeout(peekTimer)
})

// ---- Derived states ----
const hidePwd = computed(() => props.passwordLength > 0 && !props.showPassword)
const showPwd = computed(() => props.passwordLength > 0 && props.showPassword)

const peekLX = computed(() => (showPwd.value ? (isPurplePeeking.value ? 4 : -4) : isLookingAtEachOther.value ? 3 : undefined))
const peekLY = computed(() => (showPwd.value ? (isPurplePeeking.value ? 5 : -4) : isLookingAtEachOther.value ? 4 : undefined))
const hideLX = computed(() => (showPwd.value ? -4 : isLookingAtEachOther.value ? 0 : undefined))
const hideLY = computed(() => (showPwd.value ? -4 : isLookingAtEachOther.value ? -4 : undefined))
const hidePX = computed(() => (showPwd.value ? -5 : undefined))
const hidePY = computed(() => (showPwd.value ? -4 : undefined))

// ---- Purple character ----
const purpleSkew = computed(() => calcSkew(purpleRef.value))
const purpleFace = computed(() => calcFace(purpleRef.value))

const purpleStyle = computed(() => ({
  left: '70px', width: '180px', height: (props.isTyping || hidePwd.value) ? '440px' : '400px',
  backgroundColor: '#6C3FF5', borderRadius: '10px 10px 0 0', zIndex: 1,
  transform: showPwd.value ? 'skewX(0deg)' : (props.isTyping || hidePwd.value) ? `skewX(${purpleSkew.value - 12}deg) translateX(40px)` : `skewX(${purpleSkew.value}deg)`,
}))

const purpleEyes = computed(() => showPwd.value ? { left: '20px', top: '35px' }
  : isLookingAtEachOther.value ? { left: '55px', top: '65px' }
  : { left: `${45 + purpleFace.value.x}px`, top: `${40 + purpleFace.value.y}px` })

const purpleEye1Style = computed(() => ({ width: '18px', height: isPurpleBlinking.value ? '2px' : '18px' }))
const purpleEye2Style = computed(() => ({ width: '18px', height: isPurpleBlinking.value ? '2px' : '18px' }))
const purplePupil1Style = computed(() => {
  const o = pupilOffset(purpleEye1.value, 5, peekLX.value, peekLY.value)
  return { width: '7px', height: '7px', transform: `translate(${o.x}px, ${o.y}px)` }
})
const purplePupil2Style = computed(() => {
  const o = pupilOffset(purpleEye2.value, 5, peekLX.value, peekLY.value)
  return { width: '7px', height: '7px', transform: `translate(${o.x}px, ${o.y}px)` }
})

// ---- Black character ----
const blackSkew = computed(() => calcSkew(blackRef.value))
const blackFace = computed(() => calcFace(blackRef.value))

const blackStyle = computed(() => ({
  left: '240px', width: '120px', height: '310px', backgroundColor: '#2D2D2D', borderRadius: '8px 8px 0 0', zIndex: 2,
  transform: showPwd.value ? 'skewX(0deg)'
    : isLookingAtEachOther.value ? `skewX(${blackSkew.value * 1.5 + 10}deg) translateX(20px)`
    : (props.isTyping || hidePwd.value) ? `skewX(${blackSkew.value * 1.5}deg)` : `skewX(${blackSkew.value}deg)`,
}))

const blackEyes = computed(() => showPwd.value ? { left: '10px', top: '28px' }
  : isLookingAtEachOther.value ? { left: '32px', top: '12px' }
  : { left: `${26 + blackFace.value.x}px`, top: `${32 + blackFace.value.y}px` })

const blackEye1Style = computed(() => ({ width: '16px', height: isBlackBlinking.value ? '2px' : '16px' }))
const blackEye2Style = computed(() => ({ width: '16px', height: isBlackBlinking.value ? '2px' : '16px' }))
const blackPupil1Style = computed(() => {
  const o = pupilOffset(blackEye1.value, 4, hideLX.value, hideLY.value)
  return { width: '6px', height: '6px', transform: `translate(${o.x}px, ${o.y}px)` }
})
const blackPupil2Style = computed(() => {
  const o = pupilOffset(blackEye2.value, 4, hideLX.value, hideLY.value)
  return { width: '6px', height: '6px', transform: `translate(${o.x}px, ${o.y}px)` }
})

// ---- Orange character ----
const orangeSkew = computed(() => calcSkew(orangeRef.value))
const orangeFace = computed(() => calcFace(orangeRef.value))

const orangeStyle = computed(() => ({
  left: '0px', width: '240px', height: '200px', backgroundColor: '#FF9B6B', borderRadius: '120px 120px 0 0', zIndex: 3,
  transform: showPwd.value ? 'skewX(0deg)' : `skewX(${orangeSkew.value}deg)`,
}))

const orangeEyes = computed(() => showPwd.value ? { left: '50px', top: '85px' }
  : { left: `${82 + orangeFace.value.x}px`, top: `${90 + orangeFace.value.y}px` })

const orangePupil1Style = computed(() => {
  const o = pupilOffset(orangePupil1.value, 5, hidePX.value, hidePY.value)
  return { width: '12px', height: '12px', transform: `translate(${o.x}px, ${o.y}px)` }
})
const orangePupil2Style = computed(() => {
  const o = pupilOffset(orangePupil2.value, 5, hidePX.value, hidePY.value)
  return { width: '12px', height: '12px', transform: `translate(${o.x}px, ${o.y}px)` }
})

// ---- Yellow character ----
const yellowSkew = computed(() => calcSkew(yellowRef.value))
const yellowFace = computed(() => calcFace(yellowRef.value))

const yellowStyle = computed(() => ({
  left: '310px', width: '140px', height: '230px', backgroundColor: '#E8D754', borderRadius: '70px 70px 0 0', zIndex: 4,
  transform: showPwd.value ? 'skewX(0deg)' : `skewX(${yellowSkew.value}deg)`,
}))

const yellowEyes = computed(() => showPwd.value ? { left: '20px', top: '35px' }
  : { left: `${52 + yellowFace.value.x}px`, top: `${40 + yellowFace.value.y}px` })

const yellowPupil1Style = computed(() => {
  const o = pupilOffset(yellowPupil1.value, 5, hidePX.value, hidePY.value)
  return { width: '12px', height: '12px', transform: `translate(${o.x}px, ${o.y}px)` }
})
const yellowPupil2Style = computed(() => {
  const o = pupilOffset(yellowPupil2.value, 5, hidePX.value, hidePY.value)
  return { width: '12px', height: '12px', transform: `translate(${o.x}px, ${o.y}px)` }
})

const yellowMouth = computed(() => showPwd.value ? { left: '10px', top: '88px' }
  : { left: `${40 + yellowFace.value.x}px`, top: `${88 + yellowFace.value.y}px` })
</script>

<style scoped>
.chars-wrapper { position: relative; }
.char-obj { position: absolute; bottom: 0; transition: all 0.7s ease-in-out; transform-origin: bottom center; }

.eye-row { position: absolute; display: flex; gap: 24px; transition: all 0.7s ease-in-out; }
.char-obj:nth-child(3) .eye-row,
.char-obj:nth-child(4) .eye-row { transition: all 0.2s ease-out; }

.eyeball { background: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; overflow: hidden; transition: all 0.15s; flex-shrink: 0; }
.pupil { background: #2D2D2D; border-radius: 50%; transition: transform 0.1s ease-out; }
.pupil-dot { background: #2D2D2D; border-radius: 50%; transition: transform 0.1s ease-out; position: relative; z-index: 10; }

.mouth { position: absolute; width: 80px; height: 4px; background-color: #2D2D2D; border-radius: 9999px; transition: all 0.2s ease-out; }
</style>