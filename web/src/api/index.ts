import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const stockApi = {
  getStocks: (params?: { page?: number; page_size?: number; date?: string }) =>
    api.get('/stocks', { params }) as Promise<any>,
  
  getStockDetail: (code: string, params?: { start_date?: string; end_date?: string }) =>
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
  
  getTodayPatterns: (params?: { signal?: string; limit?: number }) =>
    api.get('/patterns/today', { params }) as Promise<any>,
}

export const strategyApi = {
  getStrategies: () => api.get('/strategies') as Promise<any>,
  
  runStrategy: (strategy: string, date?: string) =>
    api.post('/strategies/run', { strategy, date }) as Promise<any>,
  
  getResults: (params?: { strategy?: string; date?: string; limit?: number }) =>
    api.get('/strategies/results', { params }) as Promise<any>,
}

export const backtestApi = {
  runBacktest: (params: {
    strategy: string
    start_date: string
    end_date: string
    initial_capital: number
  }) => api.post('/backtest', params) as Promise<any>,
  
  getBacktest: (id: string) => api.get(`/backtest/${id}`) as Promise<any>,
}

export const selectionApi = {
  getConditions: () => api.get('/selection/conditions') as Promise<any>,
  
  runSelection: (conditions: any) => api.post('/selection', conditions) as Promise<any>,
  
  getHistory: (params?: { limit?: number }) =>
    api.get('/selection/history', { params }) as Promise<any>,
}

export const fundFlowApi = {
  getFundFlow: (code: string, days?: number) =>
    api.get(`/fund-flow/${code}`, { params: { days } }) as Promise<any>,
  
  getIndustryFundFlow: (date?: string, limit?: number) =>
    api.get('/fund-flow/sector/industry', { params: { date, limit } }) as Promise<any>,
  
  getConceptFundFlow: (date?: string, limit?: number) =>
    api.get('/fund-flow/sector/concept', { params: { date, limit } }) as Promise<any>,
}

export const attentionApi = {
  getList: () => api.get('/attention') as Promise<any>,
  
  add: (code: string) => api.post('/attention', { code }) as Promise<any>,
  
  remove: (code: string) => api.delete(`/attention/${code}`) as Promise<any>,
}

export default api
