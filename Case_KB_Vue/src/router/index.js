import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/show',
    name: 'Show',
    component: () => import('@/views/Show.vue')
  },
  {
    path: '/email-classification',
    name: 'EmailClassification',
    component: () => import('@/views/EmailClassification.vue')
  },
  {
    path: '/case-manager',
    name: 'CaseManager',
    component: () => import('@/views/CaseManager.vue')
  },
  {
    path: '/audit-manager',
    name: 'AuditManager',
    component: () => import('@/views/AuditManager.vue')
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router 