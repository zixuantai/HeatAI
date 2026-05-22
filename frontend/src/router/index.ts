import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/modules/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/pages/RegisterUser.vue'),
    meta: { guest: true }
  },
  {
    path: '/register-user',
    name: 'RegisterUser',
    component: () => import('@/pages/RegisterUser.vue'),
    meta: { guest: true }
  },
  {
    path: '/register-admin',
    name: 'RegisterAdmin',
    component: () => import('@/pages/RegisterAdmin.vue'),
    meta: { guest: true }
  },
  {
    path: '/chat',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: false },
    children: [
      {
        path: ':sessionId?',
        name: 'ChatSession',
        component: () => import('@/pages/Chat.vue'),
        props: true
      }
    ]
  },
  {
    path: '/documents',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Documents',
        component: () => import('@/pages/Documents.vue')
      }
    ]
  },
  {
    path: '/organizations',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Organizations',
        component: () => import('@/pages/Organizations.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  if (to.meta.guest && authStore.isAuthenticated) {
    next('/chat')
    return
  }

  next()
})

export default router
