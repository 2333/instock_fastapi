<template>
  <div class="stocks-page">
    <div class="page-header">
      <div class="header-left">
        <h1>股票列表</h1>
        <p class="subtitle">浏览和监控A股股票</p>
      </div>
      <div class="header-right">
        <div class="search-box">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input type="text" v-model="searchQuery" placeholder="搜索股票..." class="search-input">
        </div>
        <button class="btn btn-primary" @click="refreshData" :disabled="loading">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div class="filters-bar">
      <div class="filter-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.value"
          class="filter-tab"
          :class="{ active: activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="filter-options">
        <select v-model="marketFilter" class="filter-select">
          <option value="">全部市场</option>
          <option value="sh">上海</option>
          <option value="sz">深圳</option>
        </select>
        <select v-model="sortBy" class="filter-select">
          <option value="code">按代码排序</option>
          <option value="name">按名称排序</option>
          <option value="price">按价格排序</option>
          <option value="change">按涨跌幅排序</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="fetchStocks">重试</button>
    </div>

    <div v-else class="stocks-table-wrapper">
      <table class="stocks-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>价格</th>
            <th>涨跌幅</th>
            <th>成交量</th>
            <th>成交额</th>
            <th>最高</th>
            <th>最低</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="stock in filteredStocks" 
            :key="stock.code"
            @click="$router.push(`/stocks/${stock.code}`)"
          >
            <td>
              <span class="stock-code">{{ stock.code }}</span>
            </td>
            <td>
              <span class="stock-name">{{ stock.name || '-' }}</span>
            </td>
            <td :class="getChangeClass(stock.change_rate)">
              {{ stock.close ? stock.close.toFixed(2) : '-' }}
            </td>
            <td :class="getChangeClass(stock.change_rate)">
              {{ formatChange(stock.change_rate) }}
            </td>
            <td>{{ formatVolume(stock.vol) }}</td>
            <td>{{ formatTurnover(stock.amount) }}</td>
            <td>{{ stock.high ? stock.high.toFixed(2) : '-' }}</td>
            <td>{{ stock.low ? stock.low.toFixed(2) : '-' }}</td>
            <td>
              <div class="action-btns">
                <button class="action-btn" title="查看图表" @click.stop="$router.push(`/stocks/${stock.code}`)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                  </svg>
                </button>
                <button class="action-btn" title="添加到关注" @click.stop="addToWatchlist(stock)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
      <span class="page-info">第 {{ currentPage }} 页</span>
      <button class="page-btn" :disabled="stocks.length < pageSize" @click="currentPage++">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { stockApi, attentionApi } from '@/api'

interface Stock {
  code: string
  name: string | null
  close: number | null
  change_rate: number | null
  vol: number | null
  amount: number | null
  high: number | null
  low: number | null
}

const searchQuery = ref('')
const activeTab = ref('all')
const marketFilter = ref('')
const sortBy = ref('code')
const currentPage = ref(1)
const pageSize = 50
const loading = ref(false)
const error = ref('')

const stocks = ref<Stock[]>([])

const tabs = [
  { label: '全部', value: 'all' },
  { label: '涨幅榜', value: 'gainers' },
  { label: '跌幅榜', value: 'losers' },
  { label: '成交量', value: 'volume' },
]

const getChangeClass = (change: number | null) => {
  if (change === null) return ''
  return change >= 0 ? 'price-up' : 'price-down'
}

const formatChange = (change: number | null) => {
  if (change === null) return '-'
  const prefix = change >= 0 ? '+' : ''
  return `${prefix}${change.toFixed(2)}%`
}

const formatVolume = (volume: number | null) => {
  if (!volume) return '-'
  if (volume >= 1000000) return (volume / 1000000).toFixed(2) + 'M'
  if (volume >= 1000) return (volume / 1000).toFixed(2) + 'K'
  return volume.toString()
}

const formatTurnover = (turnover: number | null) => {
  if (!turnover) return '-'
  if (turnover >= 1000000000) return (turnover / 1000000000).toFixed(2) + 'B'
  if (turnover >= 1000000) return (turnover / 1000000).toFixed(2) + 'M'
  if (turnover >= 1000) return (turnover / 1000).toFixed(2) + 'K'
  return turnover.toString()
}

const filteredStocks = computed(() => {
  let result = [...stocks.value]

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(s => 
      (s.code && s.code.toLowerCase().includes(query)) || 
      (s.name && s.name.toLowerCase().includes(query))
    )
  }

  if (activeTab.value === 'gainers') {
    result = result.filter(s => (s.change_rate || 0) > 0)
  } else if (activeTab.value === 'losers') {
    result = result.filter(s => (s.change_rate || 0) < 0)
  }

  if (marketFilter.value === 'sh') {
    result = result.filter(s => s.code && s.code.startsWith('6'))
  } else if (marketFilter.value === 'sz') {
    result = result.filter(s => s.code && (s.code.startsWith('0') || s.code.startsWith('3')))
  }

  result.sort((a, b) => {
    switch (sortBy.value) {
      case 'name': return (a.name || '').localeCompare(b.name || '')
      case 'price': return (b.close || 0) - (a.close || 0)
      case 'change': return (b.change_rate || 0) - (a.change_rate || 0)
      default: return (a.code || '').localeCompare(b.code || '')
    }
  })

  return result
})

const getLatestTradeDate = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

const fetchStocks = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await stockApi.getStocks({ 
      page: currentPage.value, 
      page_size: pageSize,
      date: getLatestTradeDate()
    })
    stocks.value = data || []
  } catch (e: any) {
    error.value = e.message || '获取股票数据失败'
    stocks.value = []
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchStocks()
}

const addToWatchlist = async (stock: Stock) => {
  try {
    await attentionApi.add(stock.code)
    alert(`已添加 ${stock.name || stock.code} 到关注列表`)
  } catch (e: any) {
    alert(e.message || '添加失败')
  }
}

onMounted(() => {
  fetchStocks()
})

watch(currentPage, () => {
  fetchStocks()
})
</script>

<style scoped lang="scss">
.stocks-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.header-right {
  display: flex;
  gap: 12px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.4);

  svg {
    flex-shrink: 0;
  }
}

.search-input {
  width: 200px;
  padding: 10px 0;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;

  &:focus {
    outline: none;
  }

  &::placeholder {
    color: rgba(255, 255, 255, 0.4);
  }
}

.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.btn-primary {
    background: #2962FF;
    color: white;

    &:hover:not(:disabled) {
      background: #1E53E5;
    }
  }
}

.filters-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.filter-tabs {
  display: flex;
  gap: 4px;
}

.filter-tab {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  &.active {
    background: rgba(41, 98, 255, 0.15);
    color: #2962FF;
  }
}

.filter-options {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(26, 26, 26, 0.5);
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;

  p {
    margin: 16px 0;
    color: rgba(255, 255, 255, 0.6);
  }
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #2962FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.stocks-table-wrapper {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.stocks-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    padding: 14px 16px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  th {
    background: rgba(26, 26, 26, 0.95);
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
  }

  td {
    font-size: 13px;
  }

  tbody tr {
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.03);
    }
  }
}

.stock-code {
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.stock-name {
  color: rgba(255, 255, 255, 0.7);
}

.price-up {
  color: #00C853;
}

.price-down {
  color: #FF1744;
}

.action-btns {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.05);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.page-info {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}
</style>
