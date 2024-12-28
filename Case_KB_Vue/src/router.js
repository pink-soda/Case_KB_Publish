import { createRouter, createWebHistory } from 'vue-router'
import Show from './components/Show.vue'
import EmailClassification from './components/EmailClassification.vue'
import CaseManager from './components/CaseManager.vue'
import AuditManager from './components/AuditManager.vue'

const routes = [
  {
    path: '/',
    redirect: '/show'
  },
  {
    path: '/show',
    name: 'Show',
    component: Show
  },
  {
    path: '/email-classification',
    name: 'EmailClassification',
    component: EmailClassification
  },
  {
    path: '/case-manager',
    name: 'CaseManager',
    component: CaseManager
  },
  {
    path: '/audit-manager',
    name: 'AuditManager',
    component: AuditManager
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 