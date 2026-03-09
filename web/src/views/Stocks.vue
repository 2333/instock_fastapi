<template>
  <div class="stocks-page">
    <div class="page-header">
      <div class="header-left">
        <h1>{{ pageTitle }}</h1>
        <p class="subtitle">{{ pageSubtitle }}</p>
      </div>
      <div class="header-right">
        <div class="search-box" v-if="activeTab === 'stocks'">
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
          @click="switchTab(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="filter-options">
        <label class="date-filter" v-if="activeTab === 'stocks'">
          <span>交易日</span>
          <div class="date-input-wrapper">
            <input 
              ref="dateInput"
              v-model="selectedDate" 
              type="date" 
              class="filter-input date-input"
            >
            <svg class="date-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
          </div>
        </label>
        <select v-model="marketFilter" class="filter-select" v-if="activeTab === 'stocks'">
          <option value="">全部市场</option>
          <option value="sh">上海</option>
          <option value="sz">深圳</option>
        </select>
        <select v-model="changeFilter" class="filter-select" v-if="activeTab === 'stocks'">
          <option value="all">全部涨跌</option>
          <option value="up">仅上涨</option>
          <option value="down">仅下跌</option>
          <option value="flat">仅平盘</option>
        </select>
        <input
          v-model.number="minAmount"
          type="number"
          min="0"
          step="1000000"
          class="filter-input"
          placeholder="最小成交额"
          v-if="activeTab === 'stocks'"
        >
      </div>
    </div>
    <div class="date-hint">
      <span v-if="effectiveDate">当前展示交易日：{{ effectiveDate }}</span>
      <span v-if="isDateFallback" class="date-fallback">
        （{{ selectedDate }} 无数据，已回退到最近交易日）
      </span>
    </div>

    <div class="info-bar">
      <span v-if="effectiveDate && activeTab === 'stocks'">当前交易日：{{ effectiveDate }}</span>
      <span v-if="totalCount > 0" class="total-count">共 {{ totalCount }} {{ unitText }}</span>
      <span v-if="isDateFallback" class="date-fallback">
        （{{ selectedDate }} 无数据，已回退到最近交易日）
      </span>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="fetchData">重试</button>
    </div>

    <div v-else class="data-table-wrapper">
      <table class="data-table" v-if="activeTab === 'stocks'">
        <thead>
          <tr>
            <th class="sortable" @click="updateSort('code')">代码 <span class="sort-indicator">{{ sortIndicator('code') }}</span></th>
            <th class="sortable" @click="updateSort('name')">名称 <span class="sort-indicator">{{ sortIndicator('name') }}</span></th>
            <th class="sortable" @click="updateSort('close')">价格 <span class="sort-indicator">{{ sortIndicator('close') }}</span></th>
            <th class="sortable" @click="updateSort('change_rate')">涨跌幅 <span class="sort-indicator">{{ sortIndicator('change_rate') }}</span></th>
            <th class="sortable" @click="updateSort('vol')">成交量 <span class="sort-indicator">{{ sortIndicator('vol') }}</span></th>
            <th class="sortable" @click="updateSort('amount')">成交额 <span class="sort-indicator">{{ sortIndicator('amount') }}</span></th>
            <th class="sortable" @click="updateSort('high')">最高 <span class="sort-indicator">{{ sortIndicator('high') }}</span></th>
            <th class="sortable" @click="updateSort('low')">最低 <span class="sort-indicator">{{ sortIndicator('low') }}</span></th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="stock in paginatedData" 
            :key="stock.code"
            @click="$router.push(`/stock/${stock.code}`)"
          >
            <td><span class="stock-code">{{ stock.code }}</span></td>
            <td><span class="stock-name">{{ stock.name || '-' }}</span></td>
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
                <button class="action-btn" title="查看图表" @click.stop="$router.push(`/stock/${stock.code}`)">
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

      <!-- 龙虎榜表格 -->
      <table class="data-table" v-else-if="activeTab === 'lhb'">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>收盘价</th>
            <th>涨跌幅</th>
            <th>龙虎榜净买额</th>
            <th>龙虎榜买入</th>
            <th>龙虎榜卖出</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in paginatedData" :key="item.code">
            <td><span class="stock-code">{{ item.code }}</span></td>
            <td><span class="stock-name">{{ item.name }}</span></td>
            <td :class="getChangeClass(item.change_rate)">{{ item.close?.toFixed(2) || '-' }}</td>
            <td :class="getChangeClass(item.change_rate)">{{ formatChange(item.change_rate) }}</td>
            <td>{{ formatTurnover(item.net_amount) }}</td>
            <td>{{ formatTurnover(item.buy_amount) }}</td>
            <td>{{ formatTurnover(item.sell_amount) }}</td>
            <td>
              <button class="action-btn" @click.stop="$router.push(`/stock/${item.code}`)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 大宗交易表格 -->
      <table class="data-table" v-else-if="activeTab === 'block_trade'">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>成交价</th>
            <th>成交量</th>
            <th>成交额</th>
            <th>溢价率</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in paginatedData" :key="item.code">
            <td><span class="stock-code">{{ item.code }}</span></td>
            <td><span class="stock-name">{{ item.name }}</span></td>
            <td>{{ item.price?.toFixed(2) || '-' }}</td>
            <td>{{ formatVolume(item.vol) }}</td>
            <td>{{ formatTurnover(item.amount) }}</td>
            <td :class="getChangeClass(item.premium_rate)">{{ formatChange(item.premium_rate) }}</td>
            <td>
              <button class="action-btn" @click.stop="$router.push(`/stock/${item.code}`)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 资金流表格 -->
      <table class="data-table" v-else-if="activeTab === 'fund_flow'">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>主力净流入</th>
            <th>超大单净流入</th>
            <th>大单净流入</th>
            <th>中单净流入</th>
            <th>小单净流入</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in paginatedData" :key="item.code">
            <td><span class="stock-code">{{ item.code }}</span></td>
            <td><span class="stock-name">{{ item.name }}</span></td>
            <td :class="getChangeClass(item.main_net_inflow)">{{ formatTurnover(item.main_net_inflow) }}</td>
            <td :class="getChangeClass(item.huge_net_inflow)">{{ formatTurnover(item.huge_net_inflow) }}</td>
            <td :class="getChangeClass(item.big_net_inflow)">{{ formatTurnover(item.big_net_inflow) }}</td>
            <td :class="getChangeClass(item.mid_net_inflow)">{{ formatTurnover(item.mid_net_inflow) }}</td>
            <td :class="getChangeClass(item.small_net_inflow)">{{ formatTurnover(item.small_net_inflow) }}</td>
            <td>
              <button class="action-btn" @click.stop="$router.push(`/stock/${item.code}`)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
      <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 页</span>
      <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
      <select v-model.number="pageSize" class="page-size-select" @change="handlePageSizeChange">
        <option :value="10">10条/页</option>
        <option :value="20">20条/页</option>
        <option :value="50">50条/页</option>
        <option :value="100">100条/页</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, inject } from 'vue'
import { stockApi, attentionApi, fundFlowApi } from '@/api'

interface Stock {
  date: string | null
  code: string
  name: string | null
  industry: string | null
  close: number | null
  change_rate: number | null
  vol: number | null
  amount: number | null
  high: number | null
  low: number | null
}

const searchQuery = ref('')
const activeTab = ref('stocks')
const marketFilter = ref('')
const changeFilter = ref('all')
const minAmount = ref<number | null>(null)
const selectedDate = ref(getTodayString())
const sortKey = ref<keyof Stock>('change_rate')
const sortDirection = ref<'asc' | 'desc'>('desc')
const currentPage = ref(1)
const pageSize = ref(50)
const loading = ref(false)
const error = ref('')
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')

const stocks = ref<Stock[]>([])
const lhbData = ref<any[]>([])
const blockTradeData = ref<any[]>([])
const fundFlowData = ref<any[]>([])
const totalCount = ref(0)

const tabs = [
  { label: '股票', value: 'stocks' },
  { label: '龙虎榜', value: 'lhb' },
  { label: '大宗交易', value: 'block_trade' },
  { label: '资金流', value: 'fund_flow' },
]

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    stocks: '股票列表',
    lhb: '龙虎榜',
    block_trade: '大宗交易',
    fund_flow: '资金流向',
  }
  return titles[activeTab.value] || '数据'
})

const pageSubtitle = computed(() => {
  const subtitles: Record<string, string> = {
    stocks: '浏览和监控A股股票',
    lhb: '每日龙虎榜数据',
    block_trade: '大宗交易数据',
    fund_flow: '个股资金流向',
  }
  return subtitles[activeTab.value] || ''
})

const unitText = computed(() => {
  const units: Record<string, string> = {
    stocks: '只股票',
    lhb: '只上榜',
    block_trade: '笔交易',
    fund_flow: '只股票',
  }
  return units[activeTab.value] || '条'
})

function getTodayString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const normalizeApiDate = (value: string | null | undefined) => {
  if (!value) return ''
  if (value.includes('-')) return value
  if (value.length === 8) {
    return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
  }
  return value
}

const effectiveDate = computed(() => {
  const firstWithDate = stocks.value.find((item) => item.date)
  return normalizeApiDate(firstWithDate?.date)
})

const isDateFallback = computed(() => {
  if (!effectiveDate.value || !selectedDate.value) return false
  return effectiveDate.value !== selectedDate.value
})

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

const filteredData = computed(() => {
  let result = [...currentData.value]

  if (searchQuery.value && activeTab.value === 'stocks') {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((s: any) => 
      (s.code && s.code.toLowerCase().includes(query)) || 
      (s.name && s.name.toLowerCase().includes(query))
    )
  }

  if (activeTab.value === 'stocks') {
    if (marketFilter.value === 'sh') {
      result = result.filter((s: any) => s.code && s.code.startsWith('6'))
    } else if (marketFilter.value === 'sz') {
      result = result.filter((s: any) => s.code && (s.code.startsWith('0') || s.code.startsWith('3')))
    }

    if (changeFilter.value === 'up') {
      result = result.filter((s: any) => (s.change_rate || 0) > 0)
    } else if (changeFilter.value === 'down') {
      result = result.filter((s: any) => (s.change_rate || 0) < 0)
    } else if (changeFilter.value === 'flat') {
      result = result.filter((s: any) => (s.change_rate || 0) === 0)
    }

    if (minAmount.value !== null && !Number.isNaN(minAmount.value)) {
      result = result.filter((s: any) => (s.amount || 0) >= minAmount.value!)
    }
  }

  if (minAmount.value !== null && !Number.isNaN(minAmount.value)) {
    result = result.filter((s) => (s.amount || 0) >= minAmount.value!)
  }

  const sorted = [...result]
  sorted.sort((a, b) => compareStock(a, b, sortKey.value, sortDirection.value))

  return sorted
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

const currentData = computed(() => {
  switch (activeTab.value) {
    case 'stocks': return stocks.value
    case 'lhb': return lhbData.value
    case 'block_trade': return blockTradeData.value
    case 'fund_flow': return fundFlowData.value
    default: return []
  }
})

const getChangeClass = (change: number | null | undefined) => {
  if (change === null || change === undefined) return ''
  return change >= 0 ? 'price-up' : 'price-down'
}

const formatChange = (change: number | null | undefined) => {
  if (change === null || change === undefined) return '-'
  const prefix = change >= 0 ? '+' : ''
  return `${prefix}${change.toFixed(2)}%`
}

const formatVolume = (volume: number | null | undefined) => {
  if (!volume) return '-'
  if (volume >= 1000000) return (volume / 1000000).toFixed(2) + 'M'
  if (volume >= 1000) return (volume / 1000).toFixed(2) + 'K'
  return volume.toString()
}

const formatTurnover = (turnover: number | null | undefined) => {
  if (!turnover) return '-'
  if (Math.abs(turnover) >= 1000000000) return (turnover / 1000000000).toFixed(2) + 'B'
  if (Math.abs(turnover) >= 1000000) return (turnover / 1000000).toFixed(2) + 'M'
  if (Math.abs(turnover) >= 1000) return (turnover / 1000).toFixed(2) + 'K'
  return turnover.toString()
}

const updateSort = (key: any) => {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortDirection.value = key === 'code' || key === 'name' ? 'asc' : 'desc'
}

const sortIndicator = (key: any) => {
  if (sortKey.value !== key) return '↕'
  return sortDirection.value === 'asc' ? '↑' : '↓'
}

const switchTab = (tab: string) => {
  activeTab.value = tab
  currentPage.value = 1
  fetchData()
}

const fetchData = async () => {
  loading.value = true
  error.value = ''
  
  try {
    switch (activeTab.value) {
      case 'stocks':
        const stockRes = await stockApi.getStocks({ 
          page: currentPage.value, 
          page_size: pageSize.value,
          date: selectedDate.value.replaceAll('-', '')
        })
        stocks.value = stockRes.items || []
        totalCount.value = stockRes.total || 0
        break
        
      case 'lhb':
        const lhbRes = await marketApi.getLHB(selectedDate.value.replaceAll('-', ''), pageSize.value * 10)
        lhbData.value = lhbRes || []
        totalCount.value = lhbData.value.length
        break
        
      case 'block_trade':
        const blockRes = await marketApi.getBlockTrades(selectedDate.value.replaceAll('-', ''), pageSize.value * 10)
        blockTradeData.value = blockRes || []
        totalCount.value = blockTradeData.value.length
        break
        
      case 'fund_flow':
        const fundRes = await marketApi.getFundFlowRank(selectedDate.value.replaceAll('-', ''), pageSize.value * 10)
        fundFlowData.value = fundRes || []
        totalCount.value = fundFlowData.value.length
        break
    }
  } catch (e: any) {
    error.value = e.message || '获取数据失败'
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchData()
}

const handlePageSizeChange = () => {
  currentPage.value = 1
  fetchData()
}

const addToWatchlist = async (stock: any) => {
  try {
    await attentionApi.add(stock.code)
    showNotification?.('success', `已添加 ${stock.name || stock.code} 到关注列表`)
  } catch (e: any) {
    showNotification?.('error', e.message || '添加失败')
  }
}

onMounted(() => {
  fetchData()
})

watch(currentPage, () => {
  fetchData()
})

watch(selectedDate, () => {
  if (currentPage.value !== 1) {
    currentPage.value = 1
    return
  }
  fetchData()
})

watch(selectedDate, () => {
  if (currentPage.value !== 1) {
    currentPage.value = 1
    return
  }
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
  align-items: center;
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

.filter-input {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(26, 26, 26, 0.5);
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }

  &::placeholder {
    color: rgba(255, 255, 255, 0.35);
  }
}

.date-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
}

.date-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.date-input {
  min-width: 155px;
  padding-right: 32px;
}

.date-icon {
  position: absolute;
  right: 10px;
  pointer-events: none;
  color: rgba(255, 255, 255, 0.5);
}

.info-bar {
  margin-bottom: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.62);
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-count {
  color: #2962FF;
  font-weight: 500;
}

.date-fallback {
  color: #fbc02d;
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

.data-table-wrapper {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.data-table {
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

  th.sortable {
    cursor: pointer;
    user-select: none;
  }

  .sort-indicator {
    display: inline-block;
    margin-left: 4px;
    color: rgba(255, 255, 255, 0.35);
    font-size: 11px;
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

.page-size-select {
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
</style>
