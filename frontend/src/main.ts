import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { Language } from 'element-plus/es/locale'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'highlight.js/styles/github.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn as Language })

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

import { useAuthStore } from '@/store/modules/auth'
const authStore = useAuthStore()
authStore.initAuth().then(() => {
  app.mount('#app')
})
