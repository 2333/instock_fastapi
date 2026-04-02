import axios from 'axios'
import { ref } from 'vue'

const TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
})

const isAuthenticated = ref(!!localStorage.getItem(TOKEN_KEY))
let refreshPromise: Promise<{ access_token: string; refresh_token: string }> | null = null

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }) as Promise<{ access_token: string; refresh_token: string }>,

  register: (username: string, email: string, password: string) =>
    api.post('/auth/register', { username, email, password }) as Promise<any>,

  refreshToken: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }) as Promise<any>,

  getMe: () => api.get('/auth/me') as Promise<any>,

  getSettings: () => api.get('/auth/settings') as Promise<any>,

  updateSettings: (settings: any) => api.put('/auth/settings', settings) as Promise<any>,

  getToken: () => localStorage.getItem(TOKEN_KEY),

  setToken: (token: string, refreshToken?: string) => {
    localStorage.setItem(TOKEN_KEY, token)
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    }
    isAuthenticated.value = true
  },

  removeToken: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    isAuthenticated.value = false
  },

  isAuthenticated: () => isAuthenticated.value,

  authState: isAuthenticated,
}

api.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const status = error.response?.status
    const originalRequest = error.config as any

    if (status === 401) {
      // refresh 请求本身失败时，不再重试，直接登出
      if (originalRequest?.url?.includes('/auth/refresh') || originalRequest?._retry) {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        isAuthenticated.value = false
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }

      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)

      if (refreshToken) {
        try {
          originalRequest._retry = true
          if (!refreshPromise) {
            refreshPromise = authApi.refreshToken(refreshToken).finally(() => {
              refreshPromise = null
            })
          }
          const res = await refreshPromise
          const newAccessToken = res.access_token
          const newRefreshToken = res.refresh_token

          authApi.setToken(newAccessToken, newRefreshToken)

          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          return api(originalRequest)
        } catch (e) {
          authApi.removeToken()
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }
      } else {
        authApi.removeToken()
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
    }

    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const stockApi = {
  getStocks: (params?: { page?: number; page_size?: number; date?: string }) =>
    api.get('/stocks', { params }) as Promise<{ items: any[]; total: number; page: number; page_size: number }>,

  getStockDetail: (code: string, params?: { start_date?: string; end_date?: string; adjust?: 'bfq' | 'qfq' | 'hfq' }) =>
    api.get(`/stocks/${code}`, { params }) as Promise<any>,
}

export const etfApi = {
  getEtfList: (params?: { page?: number; page_size?: number; date?: string }) =>
    api.get('/etf', { params }) as Promise<any>,

  getEtfDetail: (code: string) => api.get(`/etf/${code}`) as Promise<any>,
}

export const indicatorApi = {
  getIndicators: (code: string, params?: { start_date?: string; end_date?: string; limit?: number }) =>
    api.get('/indicators', { params: { code, ...params } }) as Promise<any>,

  getLatestIndicator: (code: string) =>
    api.get('/indicators/latest', { params: { code } }) as Promise<any>,
}

export const patternApi = {
  getPatterns: (code: string, params?: { start_date?: string; end_date?: string; limit?: number }) =>
    api.get('/patterns', { params: { code, ...params } }) as Promise<any>,

  getTodayPatterns: (params?: {
    signal?: string
    start_date?: string
    end_date?: string
    min_confidence?: number
    pattern_names?: string
    ema_fast?: number
    ema_slow?: number
    boll_period?: number
    boll_std?: number
    ema_signal?: string
    boll_signal?: string
    indicator_mode?: 'all' | 'any'
    limit?: number
  }) =>
    api.get('/patterns/today', { params }) as Promise<any>,
}

export const strategyApi = {
  getStrategies: () => api.get('/strategies') as Promise<any>,

  getTemplates: () => api.get('/strategies/templates') as Promise<any>,

  getMyStrategies: () => api.get('/strategies/my') as Promise<any>,

  createMyStrategy: (payload: { name: string; description?: string; params?: Record<string, unknown>; is_active?: boolean }) =>
    api.post('/strategies/my', payload) as Promise<any>,

  createMyStrategyFromSelection: (payload: { name: string; description?: string; params?: Record<string, unknown>; is_active?: boolean }) =>
    api.post('/strategies/my/from-selection', payload) as Promise<any>,

  runStrategy: (strategy: string, date?: string) =>
    api.post('/strategies/run', { strategy, date }) as Promise<any>,

  getResults: (params?: { strategy?: string; date?: string; limit?: number }) =>
    api.get('/strategies/results', { params }) as Promise<any>,
}

export const backtestApi = {
  runBacktest: (params: {
    strategy: string
    strategy_params?: Record<string, string | number>
    start_date: string
    end_date: string
    initial_capital: number
    stock_code?: string
  }) => api.post('/backtest', params) as Promise<any>,

  getBacktestHistory: (limit = 10) =>
    api.get('/backtest/history', { params: { limit } }) as Promise<any>,

  getBacktest: (id: string) => api.get(`/backtest/${id}`) as Promise<any>,
}

export const selectionApi = {
  getConditions: () => api.get('/selection/conditions') as Promise<any>,

  getTemplates: () => api.get('/selection/templates') as Promise<any>,

  getMyConditions: () => api.get('/selection/my-conditions') as Promise<any>,

  createCondition: (condition: { name: string; category: string; description?: string; params?: Record<string, any>; is_active?: boolean }) =>
    api.post('/selection/my-conditions', condition) as Promise<any>,

  updateCondition: (id: number, condition: Partial<{ name: string; category: string; description: string; params: Record<string, any>; is_active: boolean }>) =>
    api.put(`/selection/my-conditions/${id}`, condition) as Promise<any>,

  deleteCondition: (id: number) => api.delete(`/selection/my-conditions/${id}`) as Promise<any>,

  runSelection: (conditions: any) => api.post('/selection', conditions) as Promise<any>,

  getHistory: (params?: { limit?: number }) =>
    api.get('/selection/history', { params }) as Promise<any>,

  getScreeningMetadata: () => api.get('/screening/metadata') as Promise<any>,

  getTodaySummary: (params?: { date?: string; limit?: number }) =>
    api.get('/selection/today-summary', { params }) as Promise<any>,

  runScreening: (payload: { filters?: Record<string, unknown>; scope?: Record<string, unknown> }) =>
    api.post('/screening/run', payload) as Promise<any>,

  getScreeningHistory: (params?: { date?: string; limit?: number }) =>
    api.get('/screening/history', { params }) as Promise<any>,

  compareScreeningResults: (historyIds: string[]) =>
    api.post('/screening/compare', { history_ids: historyIds }) as Promise<any>,
}

export const fundFlowApi = {
  getFundFlow: (code: string, days?: number) =>
    api.get(`/fund-flow/${code}`, { params: { days } }) as Promise<any>,

  getIndustryFundFlow: (date?: string, limit?: number) =>
    api.get('/fund-flow/sector/industry', { params: { date, limit } }) as Promise<any>,

  getConceptFundFlow: (date?: string, limit?: number) =>
    api.get('/fund-flow/sector/concept', { params: { date, limit } }) as Promise<any>,
}

export const marketApi = {
  getSummary: (params?: { date?: string }) =>
    api.get('/market/summary', { params }) as Promise<any>,

  getFundFlowRank: (date?: string, limit?: number) =>
    api.get('/market/fund-flow', { params: { date, limit } }) as Promise<any>,

  getBlockTrades: (date?: string, limit?: number) =>
    api.get('/market/block-trades', { params: { date, limit } }) as Promise<any>,

  getLHB: (date?: string, limit?: number) =>
    api.get('/market/lhb', { params: { date, limit } }) as Promise<any>,

  getNorthBoundFunds: (date?: string, limit?: number) =>
    api.get('/market/north-bound', { params: { date, limit } }) as Promise<any>,

  getTaskHealth: (alertLimit?: number) =>
    api.get('/market/task-health', { params: { alert_limit: alertLimit } }) as Promise<any>,
}

export const attentionApi = {
  getList: () => api.get('/attention') as Promise<any>,

  add: (code: string, group?: string, notes?: string, alertConditions?: Record<string, any>) =>
    api.post('/attention', { code, group, notes, alert_conditions: alertConditions }) as Promise<any>,

  update: (id: number, updates: { group?: string; notes?: string; alert_conditions?: Record<string, any> }) =>
    api.put(`/attention/${id}`, updates) as Promise<any>,

  remove: (code: string) => api.delete(`/attention/${code}`) as Promise<any>,
}

export default api
