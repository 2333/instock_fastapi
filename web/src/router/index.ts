import { createRouter, createWebHistory } from 'vue-router'
import { authApi } from '@/api'
import { setAnalyticsReferrer, trackPageViewForRoute } from '@/composables/useAnalytics'
import { getPreferredHomePath } from '@/composables/useUserPreferences'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/home',
    name: 'Home',
    redirect: () => getPreferredHomePath(),
    meta: { title: '首页' }
  },
  {
    path: '/',
    name: 'HomeWorkbench',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '首页工作台', analyticsPage: true, hideSidebar: true }
  },
  {
    path: '/workspace',
    name: 'Workspace',
    component: () => import('@/views/Workspace.vue'),
    meta: { title: 'TradingView 工作台（保留入口）', hideSidebar: true }
  },
  {
    path: '/stocks',
    name: 'Stocks',
    component: () => import('@/views/Stocks.vue'),
    meta: { title: '股票列表', hideSidebar: true }
  },
  {
    path: '/stock/:code',
    name: 'StockDetail',
    component: () => import('@/views/StockDetail.vue'),
    meta: { title: '个股详情', analyticsPage: true, hideSidebar: true }
  },
  {
    path: '/patterns',
    name: 'Patterns',
    component: () => import('@/views/Patterns.vue'),
    meta: { title: '形态识别', hideSidebar: true }
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: () => import('@/views/Backtest.vue'),
    meta: { title: '策略回测', analyticsPage: true, hideSidebar: true }
  },
  {
    path: '/selection',
    name: 'Selection',
    component: () => import('@/views/Selection.vue'),
    meta: { title: '策略选股', analyticsPage: true, hideSidebar: true }
  },
  {
    path: '/attention',
    name: 'Attention',
    component: () => import('@/views/Attention.vue'),
    meta: { title: '我的关注', analyticsPage: true, hideSidebar: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: '系统设置', hideSidebar: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || 'InStock'} - 智能股票分析平台`
  
  const isPublic = to.meta.public
  const isAuthenticated = authApi.isAuthenticated()
  
  if (!isPublic && !isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && isAuthenticated) {
    next(getPreferredHomePath())
  } else {
    next()
  }
})

router.afterEach((to, from) => {
  const hasSourceRoute = from.matched.length > 0

  if (hasSourceRoute && from.path !== to.path) {
    setAnalyticsReferrer(from.path)
  } else {
    setAnalyticsReferrer(null)
  }

  if (!to.meta.analyticsPage || !authApi.isAuthenticated()) {
    return
  }

  if (to.path === from.path && to.name === from.name) {
    return
  }

  trackPageViewForRoute(to, hasSourceRoute ? from : null)
})

export default router
